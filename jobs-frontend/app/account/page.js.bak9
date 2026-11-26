import Link from 'next/link';
import { redirect } from 'next/navigation';
import { getUser } from '@/lib/session';
import LogoutButton from '@/components/LogoutButton';

export const metadata = { title: 'Your account', robots: { index: false, follow: false } };

export default async function AccountPage() {
  const user = await getUser();
  if (!user) redirect('/login?next=/account');
  return (
    <div className="page">
      <h1>Your account</h1>
      <dl className="profile">
        <div><dt>Name</dt><dd>{user.name}</dd></div>
        <div><dt>Email</dt><dd>{user.email}</dd></div>
      </dl>
      <div className="actions">
        <Link href="/account/password" className="btn btn--primary">Change password</Link>
        <LogoutButton />
      </div>
    </div>
  );
}
