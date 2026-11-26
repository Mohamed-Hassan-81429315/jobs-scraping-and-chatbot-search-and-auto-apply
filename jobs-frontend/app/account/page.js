import Link from 'next/link';
import { redirect } from 'next/navigation';
import { getUser } from '../../lib/auth';

export const metadata = {
  title: 'My profile',
  description: 'Your account details.',
  robots: { index: false, follow: false },
};

// Never show anything that looks like a credential or an internal identifier.
const HIDDEN = /pass|token|secret|remember|hash|otp|key|cookie|^id$|_id$|updated_at/i;
const LABELS = {
  name: 'Full name',
  email: 'Email',
  created_at: 'Member since',
  email_verified_at: 'Email verified',
};
const ORDER = ['name', 'email', 'created_at', 'email_verified_at'];

function label(key) {
  if (LABELS[key]) return LABELS[key];
  const text = key.replace(/_/g, ' ').trim();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function format(key, value) {
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T/.test(value)) {
    const d = new Date(value);
    if (!Number.isNaN(d.getTime())) {
      return d.toLocaleDateString('en-US', { dateStyle: 'long', timeZone: 'UTC' });
    }
  }
  return String(value);
}

export default async function AccountPage() {
  const user = await getUser();
  if (!user || typeof user !== 'object') redirect('/login?next=/account');

  const rows = Object.entries(user)
    .filter(([key, value]) =>
      !HIDDEN.test(key) &&
      value !== null && value !== undefined && value !== '' &&
      typeof value !== 'object')
    .sort(([a], [b]) => {
      const ia = ORDER.indexOf(a);
      const ib = ORDER.indexOf(b);
      return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
    });

  const display = String(user.name || user.email || 'Your account');
  const initial = display.charAt(0).toUpperCase();

  return (
    <main id="main" className="wrap" style={{ padding: '40px 0' }}>
      <section className="card" aria-labelledby="profile-title" style={{ maxWidth: 640, margin: '0 auto', padding: 28 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24 }}>
          <span
            aria-hidden="true"
            style={{
              width: 56, height: 56, borderRadius: '50%', display: 'grid', placeItems: 'center',
              fontSize: 24, fontWeight: 700, color: '#06101f',
              background: 'linear-gradient(135deg, #5eead4, #818cf8)',
            }}
          >
            {initial}
          </span>
          <div>
            <h1 id="profile-title" style={{ margin: 0, fontSize: 24 }}>My profile</h1>
            <p style={{ margin: '4px 0 0', opacity: 0.7 }}>Your account details.</p>
          </div>
        </div>

        <dl style={{ margin: 0, display: 'grid', gap: 16 }}>
          {rows.map(([key, value]) => (
            <div key={key} style={{ display: 'grid', gap: 4 }}>
              <dt style={{ fontSize: 13, opacity: 0.65 }}>{label(key)}</dt>
              <dd style={{ margin: 0, fontSize: 16, overflowWrap: 'anywhere' }}>{format(key, value)}</dd>
            </div>
          ))}
        </dl>

        <div style={{ marginTop: 28, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <Link href="/account/password" className="btn-ghost" prefetch={false}>Change password</Link>
          <Link href="/" className="btn-ghost" prefetch={false}>Back to jobs</Link>
        </div>
      </section>
    </main>
  );
}
