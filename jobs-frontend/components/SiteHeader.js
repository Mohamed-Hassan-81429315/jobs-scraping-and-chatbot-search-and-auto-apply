import Link from 'next/link';
import BrandLogo from './BrandLogo';
import LogoutButton from './LogoutButton';
import { getUser } from '@/lib/session';

export default async function SiteHeader() {
  const user = await getUser();
  return (
    <header className="site-header">
      <div className="site-header__inner">
        <BrandLogo />
        <nav aria-label="Account" className="site-header__nav">
          {user ? (
            <>
              <Link href="/account" className="navlink">{user.name}</Link>
              <LogoutButton />
            </>
          ) : (
            <>
              <Link href="/login" className="navlink">Sign in</Link>
              <Link href="/register" className="btn btn--primary">Create account</Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
