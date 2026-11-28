import { redirect } from 'next/navigation';
import { getUser } from '../../../lib/auth';
import { getProfile } from '../../../lib/profile';
import ProfileEditor from '../../../components/profile/ProfileEditor';

export const metadata = { title: 'Edit profile', robots: { index: false, follow: false } };

export default async function EditProfilePage() {
  const user = await getUser();
  if (!user) redirect('/login?next=%2Faccount%2Fprofile');
  const profile = await getProfile();
  if (!profile) redirect('/account');

  return (
    <div className="pf-page">
      <h1>Edit profile</h1>
      <ProfileEditor initial={profile} />
    </div>
  );
}
