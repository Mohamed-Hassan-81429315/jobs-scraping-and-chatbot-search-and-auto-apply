import 'server-only';
import { cookies } from 'next/headers';
import { BRAND } from './applyra-brand';

export const API_URL = process.env.API_URL || 'http://127.0.0.1:8000/api';

/** Returns the signed-in user or null. Runs on the server only. */
export async function getUser() {
  const token = (await cookies()).get(BRAND.cookie)?.value;
  if (!token) return null;
  try {
    const res = await fetch(`${API_URL}/me`, {
      headers: { Accept: 'application/json', Authorization: `Bearer ${token}` },
      cache: 'no-store',
    });
    if (!res.ok) return null;
    return (await res.json()).user ?? null;
  } catch {
    return null;
  }
}

/** Only allow same-site relative redirects. */
export function safeNext(value) {
  return typeof value === 'string' && value.startsWith('/') && !value.startsWith('//') ? value : '/';
}
