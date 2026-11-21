import Link from 'next/link';
import { redirect } from 'next/navigation';
import { getUser } from '../../lib/auth';
import AuthShell from '../../components/auth/AuthShell';
import LoginForm from '../../components/auth/LoginForm';

export const metadata = {
  title: 'Log in',
  description: 'Log in to your account.',
  robots: { index: false, follow: false },
  alternates: { canonical: '/login' },
};

export default async function LoginPage({ searchParams }) {
  if (await getUser()) redirect('/');

  const sp = await searchParams;
  const next = typeof sp?.next === 'string' ? sp.next : '/';

  return (
    <AuthShell
      title="Welcome back"
      lead="Log in to continue."
      footer={<>New here? <Link href="/register" prefetch={false}>Create an account</Link></>}
    >
      <LoginForm next={next} />
    </AuthShell>
  );
}
