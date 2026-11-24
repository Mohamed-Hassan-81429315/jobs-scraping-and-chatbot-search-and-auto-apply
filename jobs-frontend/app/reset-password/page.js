import Link from 'next/link';
import { redirect } from 'next/navigation';
import { cookies } from 'next/headers';
import { getUser } from '../../lib/auth';
import AuthShell from '../../components/auth/AuthShell';
import ResetOtpForm from '../../components/auth/ResetOtpForm';
import ResendCodeControl from '../../components/auth/ResendCodeControl';
import CopyCodeButton from '../../components/auth/CopyCodeButton';

export const metadata = {
  title: 'Enter your code',
  description: 'Enter the 6-digit code from your email and choose a new password.',
  robots: { index: false, follow: false },
  referrer: 'no-referrer', // the address may carry a one-time code: never leak it
  alternates: { canonical: '/reset-password' },
};

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default async function ResetPasswordPage({ searchParams }) {
  if (await getUser()) redirect('/');
  const sp = await searchParams;
  const jar = await cookies();
  const email = String(sp?.email ?? jar.get('reset_email')?.value ?? '').trim().toLowerCase();
  if (!EMAIL.test(email)) redirect('/forgot-password');

  // The email button adds ?code=123456. Only exactly six digits are accepted.
  const rawCode = String(sp?.code ?? '').trim();
  const code = /^\d{6}$/.test(rawCode) ? rawCode : '';

  const requestedAt = Number(sp?.sentAt ?? jar.get('reset_sent_at')?.value ?? 0);
  const sentAt = Number.isSafeInteger(requestedAt) && requestedAt > 0 && requestedAt < 4_102_444_800_000
    ? requestedAt
    : 0;

  return (
    <AuthShell
      title="Enter your code"
      lead={`If ${email} has an account, we sent it a 6-digit code. It expires in 10 minutes.`}
      footer={<Link href="/" prefetch={false}>Back to sign in</Link>}
    >
      <ResetOtpForm email={email} initialCode={code} />
      <CopyCodeButton initialCode={code} />
      <ResendCodeControl email={email} initialSentAt={sentAt} />
    </AuthShell>
  );
}
