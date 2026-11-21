'use client';

import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useId, useState } from 'react';

const FIELD = {
  name: { label: 'Full name', type: 'text', autoComplete: 'name' },
  email: { label: 'Email', type: 'email', autoComplete: 'email' },
  password: { label: 'Password', type: 'password', autoComplete: 'current-password' },
  current_password: { label: 'Current password', type: 'password', autoComplete: 'current-password' },
  password_confirmation: { label: 'Confirm password', type: 'password', autoComplete: 'new-password' },
};

const MODES = {
  login: { endpoint: 'login', fields: ['email', 'password'], submit: 'Sign in', busy: 'Signing in…' },
  register: { endpoint: 'register', fields: ['name', 'email', 'password', 'password_confirmation'], submit: 'Create account', busy: 'Creating account…', strength: true },
  forgot: { endpoint: 'forgot-password', fields: ['email'], submit: 'Send reset link', busy: 'Sending…' },
  reset: { endpoint: 'reset-password', fields: ['password', 'password_confirmation'], submit: 'Reset password', busy: 'Resetting…', strength: true },
  update: { endpoint: 'update-password', fields: ['current_password', 'password', 'password_confirmation'], submit: 'Update password', busy: 'Updating…', strength: true },
};

const NEW_PASSWORD_MODES = ['register', 'reset', 'update'];

function strength(pw) {
  let s = 0;
  if (pw.length >= 8) s++;
  if (pw.length >= 12) s++;
  if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) s++;
  if (/\d/.test(pw) && /[^A-Za-z0-9]/.test(pw)) s++;
  return s; // 0-4
}
const STRENGTH_LABEL = ['Too short', 'Weak', 'Fair', 'Good', 'Strong'];

function validate(mode, v) {
  const e = {};
  const cfg = MODES[mode];
  if (cfg.fields.includes('name') && !v.name.trim()) e.name = 'Enter your name.';
  if (cfg.fields.includes('email') && !/^\S+@\S+\.\S+$/.test(v.email)) e.email = 'Enter a valid email address.';
  if (cfg.fields.includes('current_password') && !v.current_password) e.current_password = 'Enter your current password.';
  if (cfg.fields.includes('password')) {
    if (!v.password) e.password = 'Enter a password.';
    else if (NEW_PASSWORD_MODES.includes(mode) && (v.password.length < 8 || !/[A-Za-z]/.test(v.password) || !/\d/.test(v.password)))
      e.password = 'Use at least 8 characters with a letter and a number.';
  }
  if (cfg.fields.includes('password_confirmation') && v.password !== v.password_confirmation)
    e.password_confirmation = 'Passwords do not match.';
  return e;
}

function PasswordField({ id, name, meta, value, onChange, error, showMeter, autoFocus }) {
  const [shown, setShown] = useState(false);
  const score = strength(value);
  return (
    <div className="field">
      <label htmlFor={id}>{meta.label}</label>
      <div className="field__control">
        <input
          id={id}
          name={name}
          type={shown ? 'text' : 'password'}
          autoComplete={meta.autoComplete}
          value={value}
          onChange={onChange}
          aria-invalid={!!error}
          aria-describedby={error ? `${id}-err` : undefined}
          autoFocus={autoFocus}
          required
        />
        <button type="button" className="field__toggle" onClick={() => setShown((s) => !s)} aria-pressed={shown}>
          {shown ? 'Hide' : 'Show'}
        </button>
      </div>
      {showMeter && value && (
        <div className="meter" data-score={score} aria-live="polite">
          <span className="meter__bar" />
          <span className="meter__text">Password strength: {STRENGTH_LABEL[score]}</span>
        </div>
      )}
      {error && <p className="field__error" id={`${id}-err`}>{error}</p>}
    </div>
  );
}

export default function AuthForm({ mode, next = '/' }) {
  const cfg = MODES[mode];
  const router = useRouter();
  const params = useSearchParams();
  const uid = useId();

  const resetToken = params.get('token') || '';
  const resetEmail = params.get('email') || '';

  const [values, setValues] = useState({
    name: '', email: mode === 'reset' ? resetEmail : '', password: '', current_password: '', password_confirmation: '',
  });
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState('');
  const [success, setSuccess] = useState('');
  const [pending, setPending] = useState(false);

  const missingLink = mode === 'reset' && (!resetToken || !resetEmail);

  const onChange = (e) => {
    setValues((v) => ({ ...v, [e.target.name]: e.target.value }));
    if (errors[e.target.name]) setErrors((x) => ({ ...x, [e.target.name]: undefined }));
  };

  async function onSubmit(e) {
    e.preventDefault();
    setFormError('');
    setSuccess('');
    const clientErrors = validate(mode, values);
    if (Object.keys(clientErrors).length) return setErrors(clientErrors);

    setPending(true);
    const payload = Object.fromEntries(cfg.fields.map((f) => [f, values[f]]));
    if (mode === 'reset') Object.assign(payload, { token: resetToken, email: resetEmail });

    try {
      const res = await fetch(`/api/auth/${cfg.endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({}));

      if (res.status === 422 && data.errors) {
        const mapped = Object.fromEntries(Object.entries(data.errors).map(([k, m]) => [k, m[0]]));
        return setErrors(mapped);
      }
      if (res.status === 429) return setFormError('Too many attempts. Wait a minute and try again.');
      if (!res.ok) return setFormError(data.message || 'Something went wrong. Try again.');

      if (mode === 'login' || mode === 'register') {
        router.replace(next);
        router.refresh();
        return;
      }
      setSuccess(data.message || 'Done.');
      if (mode === 'update')
        setValues((v) => ({ ...v, current_password: '', password: '', password_confirmation: '' }));
    } catch {
      setFormError('Network error. Check your connection and try again.');
    } finally {
      setPending(false);
    }
  }

  if (missingLink) {
    return (
      <div className="notice notice--error" role="alert">
        This reset link is incomplete. <Link href="/forgot-password">Request a new one</Link>.
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} noValidate className="form">
      {formError && <div className="notice notice--error" role="alert">{formError}</div>}
      {success && (
        <div className="notice notice--ok" role="status">
          {success}
          {mode === 'reset' && <> <Link href="/login">Sign in</Link></>}
        </div>
      )}

      {cfg.fields.map((name, i) => {
        const id = `${uid}-${name}`;
        const meta = FIELD[name];
        if (name === 'password' || name === 'current_password' || name === 'password_confirmation') {
          const isNew = name === 'password' && cfg.strength;
          const m = name === 'password' && NEW_PASSWORD_MODES.includes(mode) ? { ...meta, label: mode === 'update' ? 'New password' : 'Password', autoComplete: 'new-password' } : meta;
          return (
            <PasswordField key={name} id={id} name={name} meta={m} value={values[name]} onChange={onChange}
              error={errors[name]} showMeter={isNew} autoFocus={i === 0} />
          );
        }
        return (
          <div className="field" key={name}>
            <label htmlFor={id}>{meta.label}</label>
            <input
              id={id}
              name={name}
              type={meta.type}
              autoComplete={meta.autoComplete}
              value={values[name]}
              onChange={onChange}
              aria-invalid={!!errors[name]}
              aria-describedby={errors[name] ? `${id}-err` : undefined}
              autoFocus={i === 0}
              required
            />
            {errors[name] && <p className="field__error" id={`${id}-err`}>{errors[name]}</p>}
          </div>
        );
      })}

      {mode === 'login' && (
        <p className="form__aside"><Link href="/forgot-password">Forgot your password?</Link></p>
      )}

      <button type="submit" className="btn btn--primary btn--block" disabled={pending}>
        {pending ? cfg.busy : cfg.submit}
      </button>
    </form>
  );
}
