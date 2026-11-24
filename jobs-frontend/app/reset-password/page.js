import Link from 'next/link';
import { redirect } from 'next/navigation';
import { getUser } from '../../lib/auth';
import AuthShell from '../../components/auth/AuthShell';
import ResetOtpForm from '../../components/auth/ResetOtpForm';
import ResendCodeControl from '../../components/auth/ResendCodeControl';

export const metadata = {
  title: 'Enter your code',
  description: 'Enter the 6-digit code from your email and choose a new password.',
  robots: { index: false, follow: false },
  alternates: { canonical: '/reset-password' },
};

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default async function ResetPasswordPage({ searchParams }) {
  if (await getUser()) redirect('/');
  const sp = await searchParams;
  const email = String(sp?.email ?? '').trim().toLowerCase();
  if (!EMAIL.test(email)) redirect('/forgot-password');

  const requestedAt = Number(sp?.sentAt ?? 0);
  const sentAt = Number.isSafeInteger(requestedAt) && requestedAt > 0 && requestedAt < 4_102_444_800_000
    ? requestedAt
    : 0;

  return (
    <AuthShell
      title="Enter your code"
      lead={`If ${email} has an account, we sent it a 6-digit code. It expires in 10 minutes.`}
      footer={<Link href="/" prefetch={false}>Back to sign in</Link>}
    >
      <ResetOtpForm email={email} />
      <ResendCodeControl email={email} initialSentAt={sentAt} />
    </AuthShell>
  );
}
