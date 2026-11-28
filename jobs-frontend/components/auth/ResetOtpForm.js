"use client";

import { useActionState, useEffect, useState } from 'react';
import { resetWithOtpAction } from '../../app/auth/otp-actions';
import Field from './Field';
import PasswordField from './PasswordField';
import SubmitButton from './SubmitButton';
import { listenForCode, sendCode, takeStashedCode } from '../../lib/otp-handoff';

const INITIAL = { errors: {}, error: '', success: '', values: {} };

export default function ResetOtpForm({ email, initialCode = '' }) {
  const [state, action] = useActionState(resetWithOtpAction, INITIAL);

  // The email button opens a NEW tab at /reset-password?email=...#code=123456.
  // 1) If the tab where the code was requested is still open, hand the code to it and let this
  //    tab close (the user stays in one tab). 2) Otherwise fill the code here.
  // Fragment and hand-off never reach a server; the address bar is cleaned right away.
  const [handedOff, setHandedOff] = useState(false);
  useEffect(() => {
    const fill = (c) => {
      const input = document.getElementById('code');
      if (input) input.value = c;
      document.getElementById('password')?.focus();
    };
    const m = /(?:^#|&)code=(\d{6})(?:&|$)/.exec(window.location.hash);
    if (m) window.history.replaceState(null, '', window.location.pathname + window.location.search);
    const stashed = m ? '' : takeStashedCode(email);

    const stop = listenForCode(email, fill); // this tab is the original and a new tab sent a code
    if (m) {
      sendCode(email, m[1]).then((accepted) => {
        if (accepted) { setHandedOff(true); window.close(); } else fill(m[1]);
      });
    } else if (stashed) {
      fill(stashed);
    }
    return stop;
  }, [email]);
  const top = state.error || state.errors.email;

  // The code came from the email link: take it out of the address bar (history, screenshots).
  useEffect(() => {
    if (!initialCode) return;
    const url = new URL(window.location.href);
    if (url.searchParams.has('code')) {
      url.searchParams.delete('code');
      window.history.replaceState(null, '', url.pathname + url.search);
    }
  }, [initialCode]);

  if (handedOff) {
    return (
      <div className="auth-form" role="status">
        <p className="alert ok">Your code was sent to the tab you started in. Continue there, and close this one.</p>
        <button type="button" className="auth-submit" onClick={() => window.close()}>Close this tab</button>
      </div>
    );
  }

  return (
    <form action={action} className="auth-form">
      {top && <p className="alert" role="alert">{top}</p>}
      <input type="hidden" name="email" value={email} />

      <Field
        id="code"
        name="code"
        label="6-digit code"
        autoComplete="one-time-code"
        inputMode="numeric"
        pattern="[0-9]{6}"
        maxLength={6}
        defaultValue={state.values.code ?? initialCode}
        error={state.errors.code}
        autoFocus={!initialCode}
      />
      <PasswordField
        id="password"
        name="password"
        label="New password"
        autoComplete="new-password"
        minLength={8}
        hint="At least 8 characters, with letters and numbers."
        error={state.errors.password}
      />
      <PasswordField
        id="password_confirmation"
        name="password_confirmation"
        label="Confirm new password"
        autoComplete="new-password"
        minLength={8}
        error={state.errors.password_confirmation}
      />
      <SubmitButton pendingLabel="Saving...">Reset password</SubmitButton>
    </form>
  );
}
