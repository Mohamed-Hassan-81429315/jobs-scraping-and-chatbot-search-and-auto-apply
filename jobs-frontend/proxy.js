import { NextResponse } from 'next/server';

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MAX_AGE = 15 * 60; // seconds; the code itself expires in 10 minutes

// Keeps the address out of the address bar, history and screenshots:
// move it into an HttpOnly cookie and redirect to a clean URL.
export function proxy(request) {
  const { nextUrl } = request;
  const params = nextUrl.searchParams;
  if (!params.has('email') && !params.has('sentAt')) return NextResponse.next();

  const email = (params.get('email') || '').trim().toLowerCase();
  const sentAt = params.get('sentAt') || '';

  const clean = nextUrl.clone();
  clean.searchParams.delete('email');
  clean.searchParams.delete('sentAt');

  const response = NextResponse.redirect(clean, 307);
  response.headers.set('Cache-Control', 'no-store');

  const options = {
    httpOnly: true,
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
    path: '/reset-password',
    maxAge: MAX_AGE,
  };
  if (EMAIL.test(email) && email.length <= 254) {
    response.cookies.set('reset_email', email, options);
    if (/^\d{10,15}$/.test(sentAt)) response.cookies.set('reset_sent_at', sentAt, options);
  }
  return response;
}

export const config = { matcher: ['/reset-password'] };
