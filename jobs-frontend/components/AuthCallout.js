import Link from 'next/link';
import { getUser } from '@/lib/session';

/** Drop <AuthCallout /> at the top of your jobs home page (app/page.js) so Sign in / Register are visible there too. */
export default async function AuthCallout() {
  const user = await getUser();
  if (user) return null;
  return (
    <section className="callout" aria-label="Account">
      <p><strong>Apply faster with a free account.</strong> Save searches, use the job assistant and auto-apply.</p>
      <div className="actions">
        <Link href="/register" className="btn btn--primary">Create account</Link>
        <Link href="/login" className="btn btn--ghost">Sign in</Link>
      </div>
    </section>
  );
}
