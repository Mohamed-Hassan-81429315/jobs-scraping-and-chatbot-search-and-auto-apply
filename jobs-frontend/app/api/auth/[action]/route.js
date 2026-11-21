import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';
import { BRAND } from '@/lib/applyra-brand';

const API = process.env.API_URL || 'http://127.0.0.1:8000/api';
const PUBLIC = new Set(['login', 'register', 'forgot-password', 'reset-password']);
const PRIVATE = new Set(['logout', 'update-password']);
const THIRTY_DAYS = 60 * 60 * 24 * 30;

async function forward(action, method, token, body) {
  return fetch(`${API}/${action}`, {
    method,
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
    cache: 'no-store',
  }).catch(() => null);
}

export async function POST(request, { params }) {
  const { action } = await params;
  if (!PUBLIC.has(action) && !PRIVATE.has(action)) {
    return NextResponse.json({ message: 'Not found.' }, { status: 404 });
  }

  const token = (await cookies()).get(BRAND.cookie)?.value;
  if (PRIVATE.has(action) && !token) {
    return NextResponse.json({ message: 'Please sign in first.' }, { status: 401 });
  }

  const body = await request.json().catch(() => ({}));
  const upstream = await forward(action, 'POST', token, body);
  if (!upstream) {
    return NextResponse.json({ message: 'The service is unreachable. Try again in a moment.' }, { status: 502 });
  }

  const data = await upstream.json().catch(() => ({}));
  const { token: newToken, ...safe } = data; // the token never reaches browser JS
  const res = NextResponse.json(safe, { status: upstream.status });

  if (upstream.ok && newToken && (action === 'login' || action === 'register')) {
    res.cookies.set(BRAND.cookie, newToken, {
      httpOnly: true,
      sameSite: 'lax',
      secure: process.env.NODE_ENV === 'production',
      path: '/',
      maxAge: THIRTY_DAYS,
    });
  }
  if (action === 'logout' || (action === 'reset-password' && upstream.ok)) {
    res.cookies.delete(BRAND.cookie);
  }
  return res;
}

export async function GET(request, { params }) {
  const { action } = await params;
  if (action !== 'me') return NextResponse.json({ message: 'Not found.' }, { status: 404 });
  const token = (await cookies()).get(BRAND.cookie)?.value;
  if (!token) return NextResponse.json({ user: null }, { status: 401 });
  const upstream = await forward('me', 'GET', token);
  const data = upstream ? await upstream.json().catch(() => ({})) : {};
  return NextResponse.json(data, { status: upstream?.status ?? 502 });
}
