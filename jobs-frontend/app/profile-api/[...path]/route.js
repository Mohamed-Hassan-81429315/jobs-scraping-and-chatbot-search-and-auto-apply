import { NextResponse } from 'next/server';
import { getToken, SESSION_COOKIE } from '../../../lib/auth';

const API = process.env.API_INTERNAL_URL || 'http://127.0.0.1:8000/api';
const MAX_BODY = 6 * 1024 * 1024;
// Only the profile endpoints are reachable through this proxy.
const ALLOWED = /^profile(\/(photo|cv|cv\/autofill|national-number))?$/;

/**
 * Browser code calls /profile-api/profile/...; this adds the Bearer token from the httpOnly
 * session cookie and forwards the raw request (multipart uploads included) to Laravel.
 */
async function handler(request, { params }) {
  const { path } = await params;
  const rel = path.join('/');
  if (!ALLOWED.test(rel)) return NextResponse.json({ message: 'Not found.' }, { status: 404 });

  const token = await getToken();
  if (!token) return NextResponse.json({ message: 'Please log in again.' }, { status: 401 });

  const mutating = request.method !== 'GET' && request.method !== 'HEAD';
  if (mutating) {
    // Same-site only: the Origin of a state-changing request must be this site.
    const origin = request.headers.get('origin');
    if (origin) {
      let host = '';
      try { host = new URL(origin).host; } catch {}
      if (host !== request.headers.get('host')) return NextResponse.json({ message: 'Forbidden.' }, { status: 403 });
    }
  }

  const headers = { Accept: 'application/json', Authorization: `Bearer ${token}` };
  let body;
  if (mutating) {
    const declared = Number(request.headers.get('content-length') || 0);
    if (declared > MAX_BODY) return NextResponse.json({ message: 'That file is too large.' }, { status: 413 });
    body = await request.arrayBuffer();
    if (body.byteLength > MAX_BODY) return NextResponse.json({ message: 'That file is too large.' }, { status: 413 });
    const type = request.headers.get('content-type');
    if (type) headers['Content-Type'] = type; // keeps the multipart boundary
  }

  const upstream = await fetch(`${API}/${rel}${request.nextUrl.search}`, {
    method: request.method,
    headers,
    body,
    cache: 'no-store',
  }).catch(() => null);

  if (!upstream) return NextResponse.json({ message: 'The service is unreachable.' }, { status: 502 });

  const out = new Headers();
  for (const name of ['content-type', 'content-disposition', 'cache-control']) {
    const value = upstream.headers.get(name);
    if (value) out.set(name, value);
  }
  out.set('X-Content-Type-Options', 'nosniff');

  const res = new NextResponse(upstream.status === 204 ? null : await upstream.arrayBuffer(), { status: upstream.status, headers: out });
  if (upstream.status === 401) res.cookies.delete(SESSION_COOKIE);
  return res;
}

export { handler as GET, handler as POST, handler as PUT, handler as DELETE };
