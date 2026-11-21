"use client";

import { useActionState } from 'react';
import { loginAction } from '../../app/auth/actions';
import Field from './Field';
import PasswordField from './PasswordField';
import SubmitButton from './SubmitButton';

const INITIAL = { errors: {}, error: '', success: '', values: {} };

export default function LoginForm({ next = '/' }) {
  const [state, action] = useActionState(loginAction, INITIAL);

  return (
    <form action={action} className="auth-form">
      {state.error && <p className="alert" role="alert">{state.error}</p>}
      <input type="hidden" name="next" value={next} />

      <Field
        id="email"
        name="email"
        type="email"
        label="Email"
        autoComplete="email"
        defaultValue={state.values.email}
        error={state.errors.email}
        maxLength={255}
        autoFocus
      />
      <PasswordField
        id="password"
        name="password"
        label="Password"
        autoComplete="current-password"
        error={state.errors.password}
      />

      <SubmitButton pendingLabel="Logging in...">Log in</SubmitButton>
    </form>
  );
}
