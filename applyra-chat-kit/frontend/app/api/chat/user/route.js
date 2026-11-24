import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

const API = process.env.API_URL || 'http://127.0.0.1:8000/api';
const KNOWN = ['applyra_token', 'token', 'auth_token', 'jobs_token', 'access_token'];

/** Returns { name } for the signed-in user, or { name: '' } for guests. Never exposes the token. */
export async function GET() {
  const store = await cookies();
  const names = new Set([
    ...KNOWN,
    ...store.getAll().map((c) => c.name).filter((n) => /token|auth|session/i.test(n)),
  ]);
  for (const n of names) {
    const raw = store.get(n)?.value;
    if (!raw) continue;
    try {
      const res = await fetch(`${API}/me`, {
        headers: { Accept: 'application/json', Authorization: `Bearer ${decodeURIComponent(raw)}` },
        cache: 'no-store',
      });
      if (!res.ok) continue;
      const j = await res.json();
      const name = j?.user?.name ?? j?.name;
      if (name) return NextResponse.json({ name: String(name).slice(0, 60) });
    } catch {}
  }
  return NextResponse.json({ name: '' });
}
