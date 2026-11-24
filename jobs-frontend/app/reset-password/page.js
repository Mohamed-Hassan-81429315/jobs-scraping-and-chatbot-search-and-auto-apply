import Link from 'next/link';
import { redirect } from 'next/navigation';
import { getUser } from '../../lib/auth';
import { resendOtpAction } from '../auth/otp-actions';
import AuthShell from '../../components/auth/AuthShell';
import ResetOtpForm from '../../components/auth/ResetOtpForm';

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

  return (
    <AuthShell
      title="Enter your code"
      lead={`If ${email} has an account, we sent it a 6-digit code. It expires in 10 minutes.`}
      footer={<Link href="/" prefetch={false}>Back to sign in</Link>}
    >
      <ResetOtpForm email={email} />
      <form action={resendOtpAction} className="auth-forgot">
        <input type="hidden" name="email" value={email} />
        <button type="submit" className="btn-link">Resend code</button>
      </form>
    </AuthShell>
  );
}
