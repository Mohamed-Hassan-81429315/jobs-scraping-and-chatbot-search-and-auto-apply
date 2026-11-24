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

function safeNext(value) {
  const v = typeof value === 'string' ? value : '/';
  return v.startsWith('/') && !v.startsWith('//') && !v.includes('\\') ? v : '/';
}

export default async function RegisterPage({ searchParams }) {
  if (await getUser()) redirect('/');

  const sp = await searchParams;
  const next = safeNext(sp?.next);

  return (
    <AuthShell
      title="Create your account"
      lead="It only takes a minute. You will log in right after."
      footer={
        <>
          Already have an account?{' '}
          <Link href={`/login?next=${encodeURIComponent(next)}`} prefetch={false}>Log in</Link>
        </>
      }
    >
      <RegisterForm next={next} />
    </AuthShell>
  );
}
