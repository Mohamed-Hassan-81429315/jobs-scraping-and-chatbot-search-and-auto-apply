"use client";

import { useActionState } from 'react';
import { resetWithOtpAction } from '../../app/auth/otp-actions';
import Field from './Field';
import PasswordField from './PasswordField';
import SubmitButton from './SubmitButton';

const INITIAL = { errors: {}, error: '', success: '', values: {} };

export default function ResetOtpForm({ email }) {
  const [state, action] = useActionState(resetWithOtpAction, INITIAL);
  const top = state.error || state.errors.email;

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
        defaultValue={state.values.code}
        error={state.errors.code}
        autoFocus
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
