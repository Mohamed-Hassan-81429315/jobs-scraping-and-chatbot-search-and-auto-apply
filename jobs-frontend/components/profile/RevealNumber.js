"use client";

import { useEffect, useRef, useState } from 'react';

/** Shows the masked national number; "Show" asks the server for the real one and hides it again after 30 s. */
export default function RevealNumber({ masked }) {
  const [value, setValue] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const timer = useRef(null);

  useEffect(() => () => clearTimeout(timer.current), []);

  async function toggle() {
    if (value) { setValue(null); return; }
    setBusy(true); setError('');
    try {
      const res = await fetch('/profile-api/profile/national-number', { credentials: 'same-origin' });
      const data = await res.json().catch(() => null);
      if (!res.ok || !data?.national_number) throw new Error();
      setValue(data.national_number);
      clearTimeout(timer.current);
      timer.current = setTimeout(() => setValue(null), 30000);
    } catch {
      setError('Could not load it. Try again.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <span className="pf-reveal">
      <span className="pf-mono" dir="ltr">{value || masked}</span>
      <button type="button" className="pf-link" onClick={toggle} disabled={busy} aria-pressed={Boolean(value)}>
        {busy ? '...' : value ? 'Hide' : 'Show'}
      </button>
      {error && <span className="pf-err" role="alert">{error}</span>}
    </span>
  );
}
