import 'server-only';
import { cookies } from 'next/headers';
import { API_URL } from './session';
import { BRAND } from './applyra-brand';

/**
 * Server-side fetch to Laravel that automatically sends the signed-in user's token.
 * Use inside Server Components / actions:  const jobs = await apiFetch('/jobs?page=1');
 * (Public endpoints work too: with no cookie it simply sends no Authorization header.)
 */
export async function apiFetch(path, init = {}) {
  const token = (await cookies()).get(BRAND.cookie)?.value;
  const res = await fetch(`${API_URL}${path}`, {
    cache: 'no-store',
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init.body ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
  if (!res.ok) throw Object.assign(new Error(`API ${res.status}`), { status: res.status });
  return res.json();
}
