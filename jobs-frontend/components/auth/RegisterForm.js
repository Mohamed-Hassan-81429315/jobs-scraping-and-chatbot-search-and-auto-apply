"use client";

import { useActionState } from 'react';
import { registerAction } from '../../app/auth/actions';
import Field from './Field';
import PasswordField from './PasswordField';
import SubmitButton from './SubmitButton';

const INITIAL = { errors: {}, error: '', success: '', values: {} };

export default function RegisterForm({ next = '/' }) {
  const [state, action] = useActionState(registerAction, INITIAL);

  return (
    <form action={action} className="auth-form">
      {state.error && <p className="alert" role="alert">{state.error}</p>}
      <input type="hidden" name="next" value={next} />

      <Field
        id="name"
        name="name"
        label="Full name"
        autoComplete="name"
        defaultValue={state.values.name}
        error={state.errors.name}
        maxLength={100}
        autoFocus
      />
      <Field
        id="email"
        name="email"
        type="email"
        label="Email"
        autoComplete="email"
        defaultValue={state.values.email}
        error={state.errors.email}
        maxLength={255}
      />
      <PasswordField
        id="password"
        name="password"
        label="Password"
        autoComplete="new-password"
        minLength={8}
        hint="At least 8 characters, with letters and numbers."
        error={state.errors.password}
      />
      <PasswordField
        id="password_confirmation"
        name="password_confirmation"
        label="Confirm password"
        autoComplete="new-password"
        minLength={8}
        error={state.errors.password_confirmation}
      />
      <SubmitButton pendingLabel="Creating account...">Create account</SubmitButton>
    </form>
  );
}
