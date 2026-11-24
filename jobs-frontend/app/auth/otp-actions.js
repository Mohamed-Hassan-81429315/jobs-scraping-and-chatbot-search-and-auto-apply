"use server";

import { redirect } from 'next/navigation';
import { api } from '../../lib/auth';

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const clean = (v) => String(v ?? '').trim();

const state = (extra = {}) => ({ errors: {}, error: '', success: '', values: {}, ...extra });

function firstErrors(data) {
  const out = {};
  for (const [field, messages] of Object.entries(data?.errors ?? {})) {
    out[field] = Array.isArray(messages) ? messages[0] : String(messages);
  }
  return out;
}

function failure(res, values) {
  if (res.status === 429) return state({ error: 'Too many attempts. Wait a minute and try again.', values });
  if (res.status === 422) {
    const errors = firstErrors(res.data);
    return state({ errors, error: Object.keys(errors).length ? '' : res.data?.message || 'Please check the form.', values });
  }
  return state({ error: 'Something went wrong. Please try again.', values });
}

/** Forgot-password form: email the code, then go enter it. */
export async function requestOtpAction(_prev, formData) {
  const email = clean(formData.get('email')).toLowerCase();
  const values = { email };

  if (!EMAIL.test(email)) return state({ errors: { email: 'Enter a valid email address.' }, values });

  const res = await api('/auth/forgot-password', { method: 'POST', body: { email } });
  if (!res.ok) return failure(res, values);

  redirect(`/reset-password?email=${encodeURIComponent(email)}&sent=1`);
}

/** "Resend code" button on the reset page. The server enforces one send per minute. */
export async function resendOtpAction(formData) {
  const email = clean(formData.get('email')).toLowerCase();
  if (!EMAIL.test(email)) redirect('/forgot-password');

  await api('/auth/forgot-password', { method: 'POST', body: { email } });
  redirect(`/reset-password?email=${encodeURIComponent(email)}&sent=1`);
}

/** Reset form: code + new password. On success the user logs in again with the new password. */
export async function resetWithOtpAction(_prev, formData) {
  const email = clean(formData.get('email')).toLowerCase();
  const code = clean(formData.get('code')).replace(/\D/g, '').slice(0, 6);
  const password = String(formData.get('password') ?? '');
  const password_confirmation = String(formData.get('password_confirmation') ?? '');
  const values = { code };

  if (code.length !== 6) return state({ errors: { code: 'Enter the 6-digit code from the email.' }, values });

  const res = await api('/auth/reset-password', {
    method: 'POST',
    body: { email, code, password, password_confirmation },
  });
  if (!res.ok) return failure(res, values);

  redirect('/?reset=1');
}
