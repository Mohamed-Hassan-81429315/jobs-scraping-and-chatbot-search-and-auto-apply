import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';
import { BRAND } from '@/lib/applyra-brand';

const API = process.env.API_URL || 'http://127.0.0.1:8000/api';
const BLOCKED = new Set(['login', 'register', 'logout', 'forgot-password', 'reset-password', 'update-password']);

/**
 * Browser code calls /api/backend/<laravel-path>; this adds the Bearer token from the
 * httpOnly cookie and forwards to Laravel. Example: fetch('/api/backend/jobs/12/apply', {method:'POST'})
 */
async function handler(request, { params }) {
  const { path } = await params;
  if (BLOCKED.has(path[0])) return NextResponse.json({ message: 'Not found.' }, { status: 404 });

  const token = (await cookies()).get(BRAND.cookie)?.value;
  const url = `${API}/${path.map(encodeURIComponent).join('/')}${request.nextUrl.search}`;
  const hasBody = !['GET', 'HEAD'].includes(request.method);

  const upstream = await fetch(url, {
    method: request.method,
    headers: {
      Accept: 'application/json',
      ...(hasBody ? { 'Content-Type': request.headers.get('content-type') || 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: hasBody ? await request.text() : undefined,
    cache: 'no-store',
  }).catch(() => null);

  if (!upstream) return NextResponse.json({ message: 'The service is unreachable.' }, { status: 502 });

  const res = new NextResponse(upstream.status === 204 ? null : await upstream.text(), {
    status: upstream.status,
    headers: { 'Content-Type': upstream.headers.get('content-type') || 'application/json' },
  });
  if (upstream.status === 401 && token) res.cookies.delete(BRAND.cookie); // expired/revoked token
  return res;
}

export { handler as GET, handler as POST, handler as PUT, handler as PATCH, handler as DELETE };
