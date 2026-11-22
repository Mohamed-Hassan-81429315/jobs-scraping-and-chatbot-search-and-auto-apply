import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { COOKIE_NAME, sameOrigin, seal } from '../../../lib/keyvault';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const WEEK = 60 * 60 * 24 * 7;
const EMBED_MODEL = process.env.OPENAI_EMBED_MODEL || 'text-embedding-3-small';

// Every failure carries a "code". The widget turns it into text in the visitor's language.
function problem(code, status) {
  return NextResponse.json({ code }, { status });
}

export async function POST(request) {
  if (!sameOrigin(request)) {
    return NextResponse.json({ code: 'forbidden_origin', error: 'Forbidden.' }, { status: 403 });
  }

  let body = null;
  try {
    body = await request.json();
  } catch {}

  const key = String(body?.key ?? '').trim();
  if (!key.startsWith('sk-') || key.length < 20 || key.length > 300 || /\s/.test(key)) {
    return problem('format', 400);
  }

  // A real (almost free) embeddings call. Listing models would succeed even for a key with no credit,
  // and the first chat message would then fail. This catches that at connect time.
  let check;
  try {
    check = await fetch('https://api.openai.com/v1/embeddings', {
      method: 'POST',
      headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: EMBED_MODEL, input: 'ping' }),
      cache: 'no-store',
      signal: AbortSignal.timeout(20000),
    });
  } catch {
    return problem('unreachable', 502);
  }

  if (check.status === 401) return problem('invalid', 400);
  if (check.status === 403) return problem('forbidden', 400);
  if (check.status === 404) return problem('model', 400);

  if (check.status === 429) {
    const info = await check.json().catch(() => null);
    const code = info?.error?.code || info?.error?.type || '';
    if (code === 'insufficient_quota') return problem('quota', 400);
    // Any other 429 only means "busy right now": the key itself is valid, so accept it.
  } else if (!check.ok) {
    return problem('upstream', 502);
  }

  let sealed;
  try {
    sealed = seal(key);
  } catch {
    return problem('server_secret', 500);
  }

  const jar = await cookies();
  jar.set(COOKIE_NAME, sealed, {
    httpOnly: true,
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
    path: '/chat-api',
    maxAge: WEEK,
  });

  return NextResponse.json({ connected: true });
}

export async function DELETE(request) {
  if (!sameOrigin(request)) {
    return NextResponse.json({ code: 'forbidden_origin', error: 'Forbidden.' }, { status: 403 });
  }
  const jar = await cookies();
  jar.delete({ name: COOKIE_NAME, path: '/chat-api' });
  return NextResponse.json({ connected: false });
}
