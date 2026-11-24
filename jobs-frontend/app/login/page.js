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

function safeNext(value) {
  const v = typeof value === 'string' ? value : '/';
  return v.startsWith('/') && !v.startsWith('//') && !v.includes('\\') ? v : '/';
}

export default async function LoginPage({ searchParams }) {
  if (await getUser()) redirect('/');

  const sp = await searchParams;
  const next = safeNext(sp?.next);
  const registered = sp?.registered === '1';

  return (
    <AuthShell
      title={registered ? 'Account created' : 'Welcome back'}
      lead={registered ? 'Your account is ready. Log in to continue.' : 'Log in to continue.'}
      footer={
        <>
          New here?{' '}
          <Link href={`/register?next=${encodeURIComponent(next)}`} prefetch={false}>Create an account</Link>
        </>
      }
    >
      <LoginForm next={next} />
    </AuthShell>
  );
}
