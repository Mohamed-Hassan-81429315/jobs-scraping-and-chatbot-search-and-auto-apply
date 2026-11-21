import { redirect } from 'next/navigation';
import { getUser } from '../../../lib/auth';
import AuthShell from '../../../components/auth/AuthShell';
import PasswordForm from '../../../components/auth/PasswordForm';

export const metadata = {
  title: 'Change password',
  description: 'Change your account password.',
  robots: { index: false, follow: false },
  alternates: { canonical: '/account/password' },
};

export default async function PasswordPage() {
  const user = await getUser();
  if (!user) redirect('/login?next=%2Faccount%2Fpassword');

  return (
    <AuthShell
      title="Change password"
      lead={`Signed in as ${user.email}.`}
    >
      <PasswordForm />
    </AuthShell>
  );
}
