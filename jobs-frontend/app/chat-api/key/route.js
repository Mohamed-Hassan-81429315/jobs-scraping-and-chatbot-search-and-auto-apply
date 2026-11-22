import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { COOKIE_NAME, sameOrigin, seal } from '../../../lib/keyvault';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const WEEK = 60 * 60 * 24 * 7;

export async function POST(request) {
  if (!sameOrigin(request)) {
    return NextResponse.json({ error: 'Forbidden.' }, { status: 403 });
  }

  let body = null;
  try {
    body = await request.json();
  } catch {}

  const key = String(body?.key ?? '').trim();
  if (key.length < 16 || key.length > 200 || /\s/.test(key)) {
    return NextResponse.json({ error: 'That does not look like a valid API key.' }, { status: 400 });
  }

  // Verify the key with Mistral before storing it.
  let check;
  try {
    check = await fetch('https://api.mistral.ai/v1/models', {
      headers: { Authorization: `Bearer ${key}` },
      cache: 'no-store',
      signal: AbortSignal.timeout(15000),
    });
  } catch {
    return NextResponse.json({ error: 'Could not reach Mistral to verify the key. Please try again.' }, { status: 502 });
  }

  if (check.status === 401 || check.status === 403) {
    return NextResponse.json({ error: 'Mistral rejected this key. Check it and try again.' }, { status: 400 });
  }
  if (!check.ok) {
    return NextResponse.json({ error: 'Mistral could not verify the key right now. Try again in a moment.' }, { status: 502 });
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
