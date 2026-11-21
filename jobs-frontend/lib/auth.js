import { cache } from 'react';
import { cookies } from 'next/headers';

export const SESSION_COOKIE = 'hirelume_session';
const API = process.env.API_INTERNAL_URL || 'http://127.0.0.1:8000/api';
const MONTH = 60 * 60 * 24 * 30;

/** Call the Laravel API from the server. Never throws. */
export async function api(path, { method = 'GET', body, token } = {}) {
  const headers = { Accept: 'application/json' };
  if (body) headers['Content-Type'] = 'application/json';
  if (token) headers.Authorization = `Bearer ${token}`;

  try {
    const res = await fetch(`${API}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      cache: 'no-store',
    });
    let data = null;
    try {
      data = await res.json();
    } catch {}
    return { ok: res.ok, status: res.status, data };
  } catch {
    return { ok: false, status: 0, data: null };
  }
}

export async function getToken() {
  const jar = await cookies();
  return jar.get(SESSION_COOKIE)?.value ?? null;
}

export async function setSession(token) {
  const jar = await cookies();
  jar.set(SESSION_COOKIE, token, {
    httpOnly: true,
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
    path: '/',
    maxAge: MONTH,
  });
}

/** The signed-in user, or null. Cached for the duration of one request. */
export const getUser = cache(async () => {
  const token = await getToken();
  if (!token) return null;
  const res = await api('/auth/me', { token });
  return res.ok ? res.data?.user ?? null : null;
});
