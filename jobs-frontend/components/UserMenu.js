import Link from 'next/link';
import { getUser } from '../lib/auth';
import { logoutAction } from '../app/auth/actions';

export default async function UserMenu() {
  const user = await getUser();

  if (!user) {
    return (
      <div className="header-right">
        <Link href="/login" className="btn-ghost" prefetch={false}>Log in</Link>
        <Link href="/register" className="btn-solid" prefetch={false}>Sign up</Link>
      </div>
    );
  }

  const initial = (user.name || user.email || '?').trim().charAt(0).toUpperCase();

  return (
    <details className="usermenu">
      <summary aria-label="Account menu">
        <span className="avatar" aria-hidden="true">{initial}</span>
        <span className="uname">{user.name}</span>
      </summary>
      <div className="usermenu-panel">
        <p className="who">{user.email}</p>
        <Link href="/account" prefetch={false}>My profile</Link>
        <Link href="/account/password" prefetch={false}>Change password</Link>
        <form action={logoutAction}>
          <button type="submit">Log out</button>
        </form>
      </div>
    </details>
  );
}
