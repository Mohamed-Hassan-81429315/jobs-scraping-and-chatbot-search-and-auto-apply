import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { COOKIE_NAME, sameOrigin, unseal } from '../../../lib/keyvault';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const API = process.env.API_INTERNAL_URL || 'http://127.0.0.1:8000/api';

export async function POST(request) {
  if (!sameOrigin(request)) {
    return NextResponse.json({ error: 'Forbidden.' }, { status: 403 });
  }

  const jar = await cookies();
  const raw = jar.get(COOKIE_NAME)?.value;
  const key = raw ? unseal(raw) : null;

  if (!key) {
    return NextResponse.json(
      { code: 'key_required', reply: 'Please connect your Mistral API key to chat.' },
      { status: 401 }
    );
  }

  let body = null;
  try {
    body = await request.json();
  } catch {}

  const message = String(body?.message ?? '').trim().slice(0, 500);
  if (!message) {
    return NextResponse.json({ reply: 'Please type a message.' }, { status: 400 });
  }

  const history = Array.isArray(body?.history)
    ? body.history
        .slice(-12)
        .map((h) => ({ role: h?.role === 'user' ? 'user' : 'bot', text: String(h?.text ?? '').slice(0, 1000) }))
        .filter((h) => h.text)
    : [];
  const lastSearch = body?.last_search && typeof body.last_search === 'object' ? body.last_search : null;

  try {
    const res = await fetch(`${API}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        'X-Mistral-Key': key,
      },
      body: JSON.stringify({ message, history, last_search: lastSearch }),
      cache: 'no-store',
      signal: AbortSignal.timeout(90000),
    });
    const data = await res.json().catch(() => ({ reply: 'Unexpected response from the server.' }));
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json(
      { code: 'unreachable', reply: 'The search service is not reachable right now.' },
      { status: 502 }
    );
  }
}
