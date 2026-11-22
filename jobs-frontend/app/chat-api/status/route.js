import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { COOKIE_NAME, unseal } from '../../../lib/keyvault';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET() {
  const jar = await cookies();
  const raw = jar.get(COOKIE_NAME)?.value;
  return NextResponse.json({ connected: Boolean(raw && unseal(raw)) });
}
