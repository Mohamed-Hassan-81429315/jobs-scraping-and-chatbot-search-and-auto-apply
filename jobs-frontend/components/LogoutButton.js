'use client';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

export default function LogoutButton({ className = 'btn btn--ghost' }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  async function signOut() {
    setBusy(true);
    await fetch('/api/auth/logout', { method: 'POST' }).catch(() => {});
    router.replace('/login');
    router.refresh();
  }
  return (
    <button type="button" className={className} onClick={signOut} disabled={busy}>
      {busy ? 'Signing out…' : 'Sign out'}
    </button>
  );
}
