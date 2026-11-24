import Link from 'next/link';
import { redirect } from 'next/navigation';
import { getUser } from '../../lib/auth';
import AuthShell from '../../components/auth/AuthShell';
import ForgotOtpForm from '../../components/auth/ForgotOtpForm';

export const metadata = {
  title: 'Reset your password',
  description: 'Get a 6-digit code by email to reset your password.',
  robots: { index: false, follow: false },
  alternates: { canonical: '/forgot-password' },
};

export default async function ForgotPasswordPage() {
  if (await getUser()) redirect('/');

  return (
    <AuthShell
      title="Reset your password"
      lead="Enter your email and we will send you a 6-digit code."
      footer={<Link href="/" prefetch={false}>Back to sign in</Link>}
    >
      <ForgotOtpForm />
    </AuthShell>
  );
}
