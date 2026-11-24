"use client";

import { useActionState, useEffect } from 'react';
import { resetWithOtpAction } from '../../app/auth/otp-actions';
import Field from './Field';
import PasswordField from './PasswordField';
import SubmitButton from './SubmitButton';

const INITIAL = { errors: {}, error: '', success: '', values: {} };

export default function ResetOtpForm({ email, initialCode = '' }) {
  const [state, action] = useActionState(resetWithOtpAction, INITIAL);
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
