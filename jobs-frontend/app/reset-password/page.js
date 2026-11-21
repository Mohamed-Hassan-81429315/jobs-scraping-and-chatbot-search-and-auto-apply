import { Suspense } from 'react';
import AuthShell from '@/components/AuthShell';
import AuthForm from '@/components/AuthForm';

export const metadata = {
  title: 'Choose a new password',
  description: 'Choose a new password for your Applyra account.',
  robots: { index: false, follow: false },
};

export default function ResetPasswordPage() {
  return (
    <AuthShell title="Choose a new password" intro="Pick something you do not use anywhere else.">
      <Suspense><AuthForm mode="reset" /></Suspense>
    </AuthShell>
  );
}
