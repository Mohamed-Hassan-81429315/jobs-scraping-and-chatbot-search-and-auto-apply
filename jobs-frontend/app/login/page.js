import { redirect } from 'next/navigation';
import { getUser } from '../../lib/auth';
import LoginView from '../../components/auth/LoginView';

export const metadata = {
  title: 'Log in',
  description: 'Log in to your account.',
  robots: { index: false, follow: false },
  alternates: { canonical: '/' },
};

export default async function LoginPage({ searchParams }) {
  if (await getUser()) redirect('/');
  return <LoginView params={await searchParams} />;
}
