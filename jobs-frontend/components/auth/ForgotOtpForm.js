"use client";

import { useActionState } from 'react';
import { requestOtpAction } from '../../app/auth/otp-actions';
import Field from './Field';
import SubmitButton from './SubmitButton';

const INITIAL = { errors: {}, error: '', success: '', values: {} };

export default function ForgotOtpForm() {
  const [state, action] = useActionState(requestOtpAction, INITIAL);

  return (
    <form action={action} className="auth-form">
      {state.error && <p className="alert" role="alert">{state.error}</p>}

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
      <SubmitButton pendingLabel="Sending code...">Send code</SubmitButton>
    </form>
  );
}
