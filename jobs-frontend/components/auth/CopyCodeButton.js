'use client';

import { useEffect, useState } from 'react';

const SIX_DIGITS = /^\d{6}$/;

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    try {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', '');
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand('copy');
      document.body.removeChild(ta);
      return ok;
    } catch {
      return false;
    }
  }
}

export default function CopyCodeButton({ initialCode = '' }) {
  const [code, setCode] = useState('');
  const [status, setStatus] = useState('idle'); // idle | copied | failed

  // The email link carries the code in the #fragment. Read it, fill the field,
  // then remove it from the address bar so it never sits in history or screenshots.
  useEffect(() => {
    const fromHash = new URLSearchParams(window.location.hash.slice(1)).get('code') || '';
    const found = SIX_DIGITS.test(fromHash) ? fromHash : SIX_DIGITS.test(initialCode) ? initialCode : '';
    if (window.location.hash) {
      window.history.replaceState(null, '', window.location.pathname + window.location.search);
    }
    if (!found) return;
    const input = document.getElementById('code');
    if (input) input.value = found;
    Promise.resolve().then(() => setCode(found));
  }, [initialCode]);

  if (!code) return null;

  async function onClick() {
    setStatus((await copyText(code)) ? 'copied' : 'failed');
  }

  const label =
    status === 'copied' ? 'Code copied ✓'
    : status === 'failed' ? "Couldn't copy: select the code and copy it"
    : 'Copy OTP code';

  return (
    <button
      type="button"
      className="btn-ghost"
      onClick={onClick}
      aria-live="polite"
      style={{ width: '100%', marginTop: 12 }}
    >
      {label}
    </button>
  );
}
