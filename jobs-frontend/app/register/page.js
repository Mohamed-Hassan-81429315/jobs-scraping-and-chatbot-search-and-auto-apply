import Link from 'next/link';
import { redirect } from 'next/navigation';
import { getUser } from '../../lib/auth';
import AuthShell from '../../components/auth/AuthShell';
import RegisterForm from '../../components/auth/RegisterForm';

export const metadata = {
  title: 'Create your account',
  description: 'Create a free account.',
  robots: { index: false, follow: false },
  alternates: { canonical: '/register' },
};

export default async function RegisterPage() {
  if (await getUser()) redirect('/');

  return (
    <AuthShell
      title="Create your account"
      lead="It only takes a minute."
      footer={<>Already have an account? <Link href="/login" prefetch={false}>Log in</Link></>}
    >
      <RegisterForm />
    </AuthShell>
  );
}
