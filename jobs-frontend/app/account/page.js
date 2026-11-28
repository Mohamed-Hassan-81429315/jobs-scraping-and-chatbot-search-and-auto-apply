import Link from 'next/link';
import { redirect } from 'next/navigation';
import { getUser } from '../../lib/auth';
import { getProfile, formatDate } from '../../lib/profile';
import LogoutButton from '../../components/LogoutButton';
import Avatar from '../../components/profile/Avatar';
import RevealNumber from '../../components/profile/RevealNumber';

export const metadata = { title: 'Your profile', robots: { index: false, follow: false } };

function Row({ label, children }) {
  return (
    <div className="pf-row">
      <dt>{label}</dt>
      <dd>{children || <span className="pf-empty">Not added</span>}</dd>
    </div>
  );
}

export default async function AccountPage() {
  const user = await getUser();
  if (!user) redirect('/login?next=%2Faccount');
  const p = (await getProfile()) ?? { ...user, skills: [] };

  return (
    <div className="pf-page">
      <header className="pf-head">
        <Avatar profile={p} size={96} />
        <div className="pf-head__text">
          <h1>{p.name}</h1>
          {p.headline && <p className="pf-headline">{p.headline}</p>}
          <p className="pf-sub">{p.email}</p>
        </div>
      </header>

      <div className="pf-actions">
        <Link href="/account/profile" className="btn btn--primary">Edit profile</Link>
        <Link href="/account/password" className="btn btn--ghost">Change password</Link>
        <LogoutButton />
      </div>

      <section className="pf-card" aria-labelledby="pf-details">
        <h2 id="pf-details">Personal details</h2>
        <dl className="pf-list">
          <Row label="Phone"><span dir="ltr">{p.phone}</span></Row>
          <Row label="Location">{p.location}</Row>
          <Row label="Birth date">{formatDate(p.birth_date)}</Row>
          <Row label="National number">
            {p.has_national_number ? <RevealNumber masked={p.national_number_masked} /> : null}
          </Row>
        </dl>
      </section>

      {p.summary && (
        <section className="pf-card" aria-labelledby="pf-about">
          <h2 id="pf-about">About</h2>
          <p className="pf-summary">{p.summary}</p>
        </section>
      )}

      <section className="pf-card" aria-labelledby="pf-skills">
        <h2 id="pf-skills">Skills</h2>
        {p.skills?.length ? (
          <ul className="pf-chips">{p.skills.map((s) => <li key={s}>{s}</li>)}</ul>
        ) : (
          <p className="pf-empty">No skills yet. Upload your CV to add them automatically.</p>
        )}
      </section>

      <section className="pf-card" aria-labelledby="pf-cv">
        <h2 id="pf-cv">CV</h2>
        {p.has_cv ? (
          <div className="pf-cv">
            <span className="pf-cv__name">{p.cv_name}</span>
            <a className="btn btn--ghost" href="/profile-api/profile/cv" download>Download</a>
          </div>
        ) : (
          <p className="pf-empty">No CV uploaded. <Link href="/account/profile" className="pf-link">Upload one</Link></p>
        )}
      </section>
    </div>
  );
}
