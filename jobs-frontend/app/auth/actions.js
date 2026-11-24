"use server";

import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { api, getToken, setSession, SESSION_COOKIE } from '../../lib/auth';

const text = (form, key) => String(form.get(key) ?? '').trim();
const raw = (form, key) => String(form.get(key) ?? '');

function safeNext(value) {
  const v = String(value ?? '');
  return v.startsWith('/') && !v.startsWith('//') && !v.includes('\\') ? v : '/';
}

function fail(res, values) {
  if (res.status === 0) {
    return { errors: {}, error: 'We could not reach the server. Please try again in a moment.', success: '', values };
  }

  const errors = {};
  for (const [field, messages] of Object.entries(res.data?.errors ?? {})) {
    errors[field] = Array.isArray(messages) ? messages[0] : String(messages);
  }

  let error = '';
  if (!Object.keys(errors).length) {
    error =
      res.status === 429
        ? 'Too many attempts. Please wait a minute and try again.'
        : 'Something went wrong. Please try again.';
  }
  return { errors, error, success: '', values };
}

export async function registerAction(_prev, formData) {
  const values = { name: text(formData, 'name'), email: text(formData, 'email') };

  const res = await api('/auth/register', {
    method: 'POST',
    body: {
      ...values,
      password: raw(formData, 'password'),
      password_confirmation: raw(formData, 'password_confirmation'),
    },
  });

  if (!res.ok) return fail(res, values);

  // The user must log in after registering: no session is created here.
  redirect(`/login?registered=1&next=${encodeURIComponent(safeNext(formData.get('next')))}`);
}

export async function loginAction(_prev, formData) {
  const values = { email: text(formData, 'email') };
  const next = safeNext(formData.get('next'));

  const res = await api('/auth/login', {
    method: 'POST',
    body: { ...values, password: raw(formData, 'password') },
  });

  if (!res.ok) return fail(res, values);

  await setSession(res.data.token);
  redirect(next);
}

export async function logoutAction() {
  const token = await getToken();
  if (token) await api('/auth/logout', { method: 'POST', token });

  const jar = await cookies();
  jar.delete(SESSION_COOKIE);
  redirect('/');
}

export async function updatePasswordAction(_prev, formData) {
  const token = await getToken();
  if (!token) redirect('/login?next=%2Faccount%2Fpassword');

  const res = await api('/auth/password', {
    method: 'PUT',
    token,
    body: {
      current_password: raw(formData, 'current_password'),
      password: raw(formData, 'password'),
      password_confirmation: raw(formData, 'password_confirmation'),
    },
  });

  if (res.status === 401) redirect('/login?next=%2Faccount%2Fpassword');
  if (!res.ok) return fail(res, {});

  return {
    errors: {},
    error: '',
    success: 'Your password was updated. Other devices were signed out.',
    values: {},
  };
}
