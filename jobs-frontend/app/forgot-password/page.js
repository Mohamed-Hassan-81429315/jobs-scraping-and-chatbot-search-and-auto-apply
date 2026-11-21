import Link from 'next/link';
import { Suspense } from 'react';
import AuthShell from '@/components/AuthShell';
import AuthForm from '@/components/AuthForm';

export const metadata = {
  title: 'Reset your password',
  description: 'Request a link to reset your Applyra password.',
  alternates: { canonical: '/forgot-password' },
  robots: { index: false, follow: true },
};

export default function ForgotPasswordPage() {
  return (
    <AuthShell title="Reset your password" intro="Enter your email and we will send you a link to choose a new password."
      footer={<><Link href="/login">Back to sign in</Link></>}>
      <Suspense><AuthForm mode="forgot" /></Suspense>
    </AuthShell>
  );
}
