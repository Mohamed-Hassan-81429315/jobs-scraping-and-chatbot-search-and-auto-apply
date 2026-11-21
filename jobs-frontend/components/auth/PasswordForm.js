"use client";

import { useActionState } from 'react';
import { updatePasswordAction } from '../../app/auth/actions';
import PasswordField from './PasswordField';
import SubmitButton from './SubmitButton';

const INITIAL = { errors: {}, error: '', success: '', values: {} };

export default function PasswordForm() {
  const [state, action] = useActionState(updatePasswordAction, INITIAL);

  return (
    <form action={action} className="auth-form">
      {state.error && <p className="alert" role="alert">{state.error}</p>}
      {state.success && <p className="alert ok" role="status">{state.success}</p>}

      <PasswordField
        id="current_password"
        name="current_password"
        label="Current password"
        autoComplete="current-password"
        error={state.errors.current_password}
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

      <SubmitButton pendingLabel="Updating...">Update password</SubmitButton>
    </form>
  );
}
