import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { COOKIE_NAME, sameOrigin, seal } from '../../../lib/keyvault';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const WEEK = 60 * 60 * 24 * 7;
const EMBED_MODEL = process.env.OPENAI_EMBED_MODEL || 'text-embedding-3-small';

export async function POST(request) {
  if (!sameOrigin(request)) {
    return NextResponse.json({ error: 'Forbidden.' }, { status: 403 });
  }

  let body = null;
  try {
    body = await request.json();
  } catch {}

  const key = String(body?.key ?? '').trim();
  if (!/^sk-[\w-]{16,}$/.test(key) || key.length > 250) {
    return NextResponse.json(
      { error: 'That does not look like an OpenAI API key. It should start with "sk-".' },
      { status: 400 }
    );
  }

  // Verify the key with a tiny embeddings request: it checks the key AND the exact permission we use.
  let check;
  try {
    check = await fetch('https://api.openai.com/v1/embeddings', {
      method: 'POST',
      headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: EMBED_MODEL, input: 'ok' }),
      cache: 'no-store',
      signal: AbortSignal.timeout(20000),
    });
  } catch {
    return NextResponse.json({ error: 'Could not reach OpenAI to verify the key. Please try again.' }, { status: 502 });
  }

  if (check.status === 401) {
    return NextResponse.json({ error: 'OpenAI rejected this key. Check it and try again.' }, { status: 400 });
  }

  if (!check.ok) {
    const info = await check.json().catch(() => null);
    const code = info?.error?.code;
    if (check.status === 429 && code === 'insufficient_quota') {
      return NextResponse.json(
        { error: 'This OpenAI account has no remaining credit. Add billing credit in your OpenAI account, then try again.' },
        { status: 400 }
      );
    }
    if (check.status === 429) {
      return NextResponse.json({ error: 'OpenAI is rate limiting this key. Try again in a moment.' }, { status: 429 });
    }
    if (check.status === 403 || check.status === 404) {
      const detail = String(info?.error?.message ?? '').slice(0, 160);
      return NextResponse.json(
        { error: `This key cannot use the required model.${detail ? ` OpenAI says: ${detail}` : ''}` },
        { status: 400 }
      );
    }
    return NextResponse.json({ error: 'OpenAI could not verify the key right now. Try again in a moment.' }, { status: 502 });
  }

  let sealed;
  try {
    sealed = seal(key);
  } catch {
    return NextResponse.json(
      { error: 'The server is missing CHAT_COOKIE_SECRET. Add it to jobs-frontend/.env.local and restart.' },
      { status: 500 }
    );
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
    return NextResponse.json({ error: 'Forbidden.' }, { status: 403 });
  }
  const jar = await cookies();
  jar.delete({ name: COOKIE_NAME, path: '/chat-api' });
  return NextResponse.json({ connected: false });
}
