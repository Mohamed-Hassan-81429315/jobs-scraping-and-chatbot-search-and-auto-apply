#!/usr/bin/env python3
"""
Installs, from the project root ("Jobs and chatbot"):

  BACKEND   Laravel + Sanctum auth API (register, login, me, logout, change password)
  FRONTEND  /login, /register, /account/password pages (Server Actions, httpOnly
            session cookie), user menu in the header
  BRAND     Hirelume name + logo, favicon, Open Graph image, web manifest,
            Organization structured data

Run:   python3 install_auth_brand.py
Every file that already exists is backed up as <name>.prepatch first.
"""
import pathlib
import shutil
import sys

ROOT = pathlib.Path(".")
BACK = ROOT / "jobs-backend"
FRONT = ROOT / "jobs-frontend"

if not (BACK / "artisan").exists() or not (FRONT / "app" / "page.js").exists():
    sys.exit("Run this from the project root (the folder that contains jobs-backend and jobs-frontend).")

FILES = {}

# =====================================================================
# BACKEND
# =====================================================================

FILES[BACK / "app/Models/User.php"] = r'''<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Foundation\Auth\User as Authenticatable;
use Illuminate\Notifications\Notifiable;
use Laravel\Sanctum\HasApiTokens;

class User extends Authenticatable
{
    use HasApiTokens, HasFactory, Notifiable;

    protected $fillable = ['name', 'email', 'password'];

    protected $hidden = ['password', 'remember_token'];

    protected function casts(): array
    {
        return [
            'email_verified_at' => 'datetime',
            'password'          => 'hashed',
        ];
    }
}
'''

FILES[BACK / "app/Http/Controllers/AuthController.php"] = r'''<?php

namespace App\Http\Controllers;

use App\Models\User;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\RateLimiter;
use Illuminate\Support\Str;
use Illuminate\Validation\Rules\Password;
use Illuminate\Validation\ValidationException;

class AuthController extends Controller
{
    private const TOKEN_DAYS = 30;

    public function register(Request $request): JsonResponse
    {
        $request->merge(['email' => Str::lower(trim((string) $request->input('email')))]);

        $data = $request->validate([
            'name'     => ['required', 'string', 'min:2', 'max:100'],
            'email'    => ['required', 'string', 'email:rfc', 'max:255', 'unique:users,email'],
            'password' => ['required', 'string', 'confirmed', Password::min(8)->letters()->numbers()],
        ]);

        $user = User::create([
            'name'     => trim($data['name']),
            'email'    => $data['email'],
            'password' => $data['password'], // hashed by the model cast
        ]);

        return $this->issueToken($user, 201);
    }

    public function login(Request $request): JsonResponse
    {
        $request->merge(['email' => Str::lower(trim((string) $request->input('email')))]);

        $data = $request->validate([
            'email'    => ['required', 'string', 'email'],
            'password' => ['required', 'string'],
        ]);

        $key = 'login:' . $data['email'] . '|' . $request->ip();

        if (RateLimiter::tooManyAttempts($key, 5)) {
            $seconds = RateLimiter::availableIn($key);

            throw ValidationException::withMessages([
                'email' => ["Too many attempts. Try again in {$seconds} seconds."],
            ])->status(429);
        }

        $user = User::where('email', $data['email'])->first();

        if (!$user || !Hash::check($data['password'], $user->password)) {
            RateLimiter::hit($key, 60);

            throw ValidationException::withMessages([
                'email' => ['These credentials do not match our records.'],
            ]);
        }

        RateLimiter::clear($key);

        return $this->issueToken($user);
    }

    public function me(Request $request): JsonResponse
    {
        return response()->json(['user' => $this->present($request->user())]);
    }

    public function logout(Request $request): JsonResponse
    {
        $request->user()->currentAccessToken()->delete();

        return response()->json(['message' => 'Logged out.']);
    }

    public function updatePassword(Request $request): JsonResponse
    {
        $data = $request->validate([
            'current_password' => ['required', 'string'],
            'password'         => [
                'required', 'string', 'confirmed', 'different:current_password',
                Password::min(8)->letters()->numbers(),
            ],
        ]);

        $user = $request->user();

        if (!Hash::check($data['current_password'], $user->password)) {
            throw ValidationException::withMessages([
                'current_password' => ['Your current password is incorrect.'],
            ]);
        }

        $user->forceFill(['password' => $data['password']])->save();

        // Sign out every other device; keep this session.
        $current = $user->currentAccessToken();
        $user->tokens()->where('id', '!=', $current->id)->delete();

        return response()->json(['message' => 'Password updated.']);
    }

    private function issueToken(User $user, int $status = 200): JsonResponse
    {
        $token = $user->createToken('web', ['*'], now()->addDays(self::TOKEN_DAYS));

        return response()->json([
            'user'       => $this->present($user),
            'token'      => $token->plainTextToken,
            'expires_at' => $token->accessToken->expires_at?->toIso8601String(),
        ], $status);
    }

    private function present(User $user): array
    {
        return ['id' => $user->id, 'name' => $user->name, 'email' => $user->email];
    }
}
'''

FILES[BACK / "routes/api.php"] = r'''<?php

use App\Http\Controllers\AuthController;
use App\Http\Controllers\JobController;
use Illuminate\Support\Facades\Route;

Route::get('/stats', [JobController::class, 'stats']);
Route::get('/jobs', [JobController::class, 'index']);
Route::get('/suggest', [JobController::class, 'suggest']);

Route::prefix('auth')->group(function () {
    Route::post('/register', [AuthController::class, 'register'])->middleware('throttle:10,1');
    Route::post('/login', [AuthController::class, 'login'])->middleware('throttle:20,1');

    Route::middleware('auth:sanctum')->group(function () {
        Route::get('/me', [AuthController::class, 'me']);
        Route::post('/logout', [AuthController::class, 'logout']);
        Route::put('/password', [AuthController::class, 'updatePassword']);
    });
});
'''

# =====================================================================
# FRONTEND: brand
# =====================================================================

FILES[FRONT / "lib/brand.js"] = r'''export const BRAND = {
  name: 'Hirelume',
  parts: ['Hire', 'lume'],
  tagline: 'Every job. One search.',
  description:
    'Hirelume searches job openings collected from many platforms in one place. Filter by location, company, remote and date, then apply on the original site.',
};
'''

FILES[FRONT / "components/Logo.js"] = r'''export function LogoMark({ size = 18 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="8 8 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="3.4"
      strokeLinecap="round"
      aria-hidden="true"
    >
      <path d="M12 11v18M28 11v18" />
      <circle cx="20" cy="20" r="4.6" />
      <path d="M13.5 20h1.9M24.6 20h1.9" />
    </svg>
  );
}
'''

FILES[FRONT / "app/icon.svg"] = r'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#5eead4"/>
      <stop offset="1" stop-color="#818cf8"/>
    </linearGradient>
  </defs>
  <rect width="40" height="40" rx="11" fill="url(#g)"/>
  <g fill="none" stroke="#06101f" stroke-width="3.4" stroke-linecap="round">
    <path d="M12 11v18M28 11v18"/>
    <circle cx="20" cy="20" r="4.6"/>
    <path d="M13.5 20h1.9M24.6 20h1.9"/>
  </g>
</svg>
'''

FILES[FRONT / "app/manifest.js"] = r'''import { BRAND } from '../lib/brand';

export default function manifest() {
  return {
    name: `${BRAND.name}: ${BRAND.tagline}`,
    short_name: BRAND.name,
    description: BRAND.description,
    start_url: '/',
    display: 'standalone',
    background_color: '#080c1a',
    theme_color: '#080c1a',
    icons: [{ src: '/icon.svg', sizes: 'any', type: 'image/svg+xml' }],
  };
}
'''

FILES[FRONT / "app/opengraph-image.js"] = r'''import { ImageResponse } from 'next/og';
import { BRAND } from '../lib/brand';

export const alt = `${BRAND.name}: ${BRAND.tagline}`;
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';

export default function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: 80,
          background: 'linear-gradient(135deg, #080c1a 0%, #1c1f52 100%)',
          color: 'white',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <div
            style={{
              width: 128,
              height: 128,
              borderRadius: 34,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: 'linear-gradient(135deg, #5eead4, #818cf8)',
            }}
          >
            <svg width="76" height="76" viewBox="8 8 24 24" fill="none" stroke="#06101f" strokeWidth="3.4" strokeLinecap="round">
              <path d="M12 11v18M28 11v18" />
              <circle cx="20" cy="20" r="4.6" />
              <path d="M13.5 20h1.9M24.6 20h1.9" />
            </svg>
          </div>
          <div style={{ fontSize: 116, fontWeight: 800, letterSpacing: -4, marginLeft: 32 }}>{BRAND.name}</div>
        </div>
        <div style={{ fontSize: 42, color: '#a3accb', marginTop: 30 }}>
          {BRAND.tagline} Search jobs from every platform.
        </div>
      </div>
    ),
    size
  );
}
'''

FILES[FRONT / "app/layout.js"] = r'''import './globals.css';
import Link from 'next/link';
import { Inter, Space_Grotesk } from 'next/font/google';
import { BRAND } from '../lib/brand';
import { LogoMark } from '../components/Logo';
import UserMenu from '../components/UserMenu';

const body = Inter({ subsets: ['latin'], variable: '--font-body', display: 'swap' });
const display = Space_Grotesk({ subsets: ['latin'], variable: '--font-display', display: 'swap' });

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000';
const DEFAULT_TITLE = `${BRAND.name}: ${BRAND.tagline} Search jobs from every platform`;

export const metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: DEFAULT_TITLE,
    template: `%s | ${BRAND.name}`,
  },
  description: BRAND.description,
  applicationName: BRAND.name,
  openGraph: {
    type: 'website',
    siteName: BRAND.name,
    title: DEFAULT_TITLE,
    description: BRAND.description,
    url: '/',
  },
  twitter: { card: 'summary_large_image' },
  robots: { index: true, follow: true },
};

export const viewport = { themeColor: '#080c1a', colorScheme: 'dark' };

const organization = {
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: BRAND.name,
  url: SITE_URL,
  logo: `${SITE_URL}/icon.svg`,
  description: BRAND.description,
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className={`${body.variable} ${display.variable}`}>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(organization).replace(/</g, '\\u003c') }}
        />
        <a className="skip" href="#main">Skip to content</a>

        <header className="site-header">
          <div className="wrap">
            <Link href="/" className="brand" aria-label={`${BRAND.name} home`}>
              <span className="brand-mark"><LogoMark /></span>
              <span>{BRAND.parts[0]}<b>{BRAND.parts[1]}</b></span>
            </Link>
            <nav className="nav" aria-label="Main">
              <Link href="/?remote=1" prefetch={false}>Remote jobs</Link>
              <Link href="/?posted=24h" prefetch={false}>New today</Link>
            </nav>
            <UserMenu />
          </div>
        </header>

        {children}

        <footer className="site-footer">
          <div className="wrap">
            <p>
              © {new Date().getFullYear()} {BRAND.name}. Listings are collected from public sources and licensed
              data providers; you apply on the original site.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
'''

# =====================================================================
# FRONTEND: auth core
# =====================================================================

FILES[FRONT / "lib/auth.js"] = r'''import { cache } from 'react';
import { cookies } from 'next/headers';

export const SESSION_COOKIE = 'hirelume_session';
const API = process.env.API_INTERNAL_URL || 'http://127.0.0.1:8000/api';
const MONTH = 60 * 60 * 24 * 30;

/** Call the Laravel API from the server. Never throws. */
export async function api(path, { method = 'GET', body, token } = {}) {
  const headers = { Accept: 'application/json' };
  if (body) headers['Content-Type'] = 'application/json';
  if (token) headers.Authorization = `Bearer ${token}`;

  try {
    const res = await fetch(`${API}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      cache: 'no-store',
    });
    let data = null;
    try {
      data = await res.json();
    } catch {}
    return { ok: res.ok, status: res.status, data };
  } catch {
    return { ok: false, status: 0, data: null };
  }
}

export async function getToken() {
  const jar = await cookies();
  return jar.get(SESSION_COOKIE)?.value ?? null;
}

export async function setSession(token) {
  const jar = await cookies();
  jar.set(SESSION_COOKIE, token, {
    httpOnly: true,
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
    path: '/',
    maxAge: MONTH,
  });
}

/** The signed-in user, or null. Cached for the duration of one request. */
export const getUser = cache(async () => {
  const token = await getToken();
  if (!token) return null;
  const res = await api('/auth/me', { token });
  return res.ok ? res.data?.user ?? null : null;
});
'''

FILES[FRONT / "app/auth/actions.js"] = r'''"use server";

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

  await setSession(res.data.token);
  redirect('/');
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
'''

# =====================================================================
# FRONTEND: auth components
# =====================================================================

FILES[FRONT / "components/auth/Field.js"] = r'''export default function Field({
  id,
  name,
  label,
  type = 'text',
  autoComplete,
  defaultValue,
  error,
  hint,
  required = true,
  maxLength,
  autoFocus = false,
}) {
  const describedBy = error ? `${id}-err` : hint ? `${id}-hint` : undefined;

  return (
    <div className="fld">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        name={name}
        type={type}
        autoComplete={autoComplete}
        defaultValue={defaultValue}
        required={required}
        maxLength={maxLength}
        autoFocus={autoFocus}
        aria-invalid={error ? 'true' : undefined}
        aria-describedby={describedBy}
      />
      {error ? (
        <p className="err" id={`${id}-err`}>{error}</p>
      ) : hint ? (
        <p className="hint" id={`${id}-hint`}>{hint}</p>
      ) : null}
    </div>
  );
}
'''

FILES[FRONT / "components/auth/PasswordField.js"] = r'''"use client";

import { useState } from 'react';

export default function PasswordField({ id, name, label, autoComplete, error, hint, minLength }) {
  const [shown, setShown] = useState(false);
  const describedBy = error ? `${id}-err` : hint ? `${id}-hint` : undefined;

  return (
    <div className="fld">
      <label htmlFor={id}>{label}</label>
      <div className="pw">
        <input
          id={id}
          name={name}
          type={shown ? 'text' : 'password'}
          autoComplete={autoComplete}
          required
          minLength={minLength}
          aria-invalid={error ? 'true' : undefined}
          aria-describedby={describedBy}
        />
        <button type="button" onClick={() => setShown(!shown)} aria-pressed={shown}>
          {shown ? 'Hide' : 'Show'}
          <span className="sr"> password</span>
        </button>
      </div>
      {error ? (
        <p className="err" id={`${id}-err`}>{error}</p>
      ) : hint ? (
        <p className="hint" id={`${id}-hint`}>{hint}</p>
      ) : null}
    </div>
  );
}
'''

FILES[FRONT / "components/auth/SubmitButton.js"] = r'''"use client";

import { useFormStatus } from 'react-dom';

export default function SubmitButton({ children, pendingLabel }) {
  const { pending } = useFormStatus();

  return (
    <button type="submit" className="auth-submit" disabled={pending}>
      {pending ? pendingLabel : children}
    </button>
  );
}
'''

FILES[FRONT / "components/auth/AuthShell.js"] = r'''export default function AuthShell({ title, lead, footer, children }) {
  return (
    <main id="main" className="auth-wrap">
      <div className="auth-card">
        <h1>{title}</h1>
        <p className="lead">{lead}</p>
        {children}
        {footer && <p className="auth-foot">{footer}</p>}
      </div>
    </main>
  );
}
'''

FILES[FRONT / "components/auth/LoginForm.js"] = r'''"use client";

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
'''

FILES[FRONT / "components/auth/RegisterForm.js"] = r'''"use client";

import { useActionState } from 'react';
import { registerAction } from '../../app/auth/actions';
import Field from './Field';
import PasswordField from './PasswordField';
import SubmitButton from './SubmitButton';

const INITIAL = { errors: {}, error: '', success: '', values: {} };

export default function RegisterForm() {
  const [state, action] = useActionState(registerAction, INITIAL);

  return (
    <form action={action} className="auth-form">
      {state.error && <p className="alert" role="alert">{state.error}</p>}

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
'''

FILES[FRONT / "components/auth/PasswordForm.js"] = r'''"use client";

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
'''

FILES[FRONT / "components/UserMenu.js"] = r'''import Link from 'next/link';
import { getUser } from '../lib/auth';
import { logoutAction } from '../app/auth/actions';

export default async function UserMenu() {
  const user = await getUser();

  if (!user) {
    return (
      <div className="header-right">
        <Link href="/login" className="btn-ghost" prefetch={false}>Log in</Link>
        <Link href="/register" className="btn-solid" prefetch={false}>Sign up</Link>
      </div>
    );
  }

  const initial = (user.name || user.email || '?').trim().charAt(0).toUpperCase();

  return (
    <details className="usermenu">
      <summary aria-label="Account menu">
        <span className="avatar" aria-hidden="true">{initial}</span>
        <span className="uname">{user.name}</span>
      </summary>
      <div className="usermenu-panel">
        <p className="who">{user.email}</p>
        <Link href="/account/password" prefetch={false}>Change password</Link>
        <form action={logoutAction}>
          <button type="submit">Log out</button>
        </form>
      </div>
    </details>
  );
}
'''

# =====================================================================
# FRONTEND: pages
# =====================================================================

FILES[FRONT / "app/login/page.js"] = r'''import Link from 'next/link';
import { redirect } from 'next/navigation';
import { getUser } from '../../lib/auth';
import AuthShell from '../../components/auth/AuthShell';
import LoginForm from '../../components/auth/LoginForm';

export const metadata = {
  title: 'Log in',
  description: 'Log in to your account.',
  robots: { index: false, follow: false },
  alternates: { canonical: '/login' },
};

export default async function LoginPage({ searchParams }) {
  if (await getUser()) redirect('/');

  const sp = await searchParams;
  const next = typeof sp?.next === 'string' ? sp.next : '/';

  return (
    <AuthShell
      title="Welcome back"
      lead="Log in to continue."
      footer={<>New here? <Link href="/register" prefetch={false}>Create an account</Link></>}
    >
      <LoginForm next={next} />
    </AuthShell>
  );
}
'''

FILES[FRONT / "app/register/page.js"] = r'''import Link from 'next/link';
import { redirect } from 'next/navigation';
import { getUser } from '../../lib/auth';
import AuthShell from '../../components/auth/AuthShell';
import RegisterForm from '../../components/auth/RegisterForm';

export const metadata = {
  title: 'Create your account',
  description: 'Create a free account.',
  robots: { index: false, follow: false },
  alternates: { canonical: '/register' },
};

export default async function RegisterPage() {
  if (await getUser()) redirect('/');

  return (
    <AuthShell
      title="Create your account"
      lead="It only takes a minute."
      footer={<>Already have an account? <Link href="/login" prefetch={false}>Log in</Link></>}
    >
      <RegisterForm />
    </AuthShell>
  );
}
'''

FILES[FRONT / "app/account/password/page.js"] = r'''import { redirect } from 'next/navigation';
import { getUser } from '../../../lib/auth';
import AuthShell from '../../../components/auth/AuthShell';
import PasswordForm from '../../../components/auth/PasswordForm';

export const metadata = {
  title: 'Change password',
  description: 'Change your account password.',
  robots: { index: false, follow: false },
  alternates: { canonical: '/account/password' },
};

export default async function PasswordPage() {
  const user = await getUser();
  if (!user) redirect('/login?next=%2Faccount%2Fpassword');

  return (
    <AuthShell
      title="Change password"
      lead={`Signed in as ${user.email}.`}
    >
      <PasswordForm />
    </AuthShell>
  );
}
'''

# =====================================================================
# CSS
# =====================================================================

CSS_MARK = "/* auth + brand */"
CSS = r'''
/* auth + brand */
.header-right { display: flex; align-items: center; gap: 6px; }
.brand b { font-weight: 700; background: linear-gradient(90deg, var(--accent), var(--accent2)); -webkit-background-clip: text; background-clip: text; color: transparent; }
.btn-ghost, .btn-solid { display: inline-flex; align-items: center; justify-content: center; padding: 8px 16px; border-radius: 12px; font-size: .9rem; font-weight: 600; cursor: pointer; border: 1px solid var(--line); background: transparent; color: var(--text); }
.btn-ghost:hover { background: var(--panel); }
.btn-solid { color: #06101f; border: 0; background: linear-gradient(135deg, var(--accent), var(--accent2)); }
.btn-solid:hover { filter: brightness(1.08); }

.usermenu { position: relative; }
.usermenu summary { list-style: none; cursor: pointer; display: flex; align-items: center; gap: 10px; padding: 4px 12px 4px 4px; border-radius: 999px; border: 1px solid var(--line); background: var(--panel); }
.usermenu summary::-webkit-details-marker { display: none; }
.avatar { width: 30px; height: 30px; border-radius: 50%; display: grid; place-items: center; font-weight: 700; font-size: .85rem; color: #06101f; background: linear-gradient(135deg, var(--accent), var(--accent2)); }
.uname { max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: .9rem; }
.usermenu-panel { position: absolute; right: 0; top: calc(100% + 8px); min-width: 230px; padding: 8px; border-radius: 16px; background: #0e1328; border: 1px solid var(--line); box-shadow: 0 30px 80px -20px rgba(0, 0, 0, .7); z-index: 50; }
.usermenu-panel .who { padding: 8px 10px 10px; border-bottom: 1px solid var(--line); margin-bottom: 6px; font-size: .82rem; color: var(--muted); overflow-wrap: anywhere; }
.usermenu-panel a, .usermenu-panel button { display: block; width: 100%; text-align: left; padding: 9px 10px; border-radius: 10px; font-size: .92rem; background: none; border: 0; color: var(--text); cursor: pointer; }
.usermenu-panel a:hover, .usermenu-panel button:hover { background: rgba(255, 255, 255, .07); }

.auth-wrap { min-height: calc(100vh - 220px); display: grid; place-items: center; padding: 48px 20px; }
.auth-card { width: 100%; max-width: 440px; padding: 34px 30px; border-radius: 24px; background: rgba(14, 19, 40, .82); border: 1px solid var(--line); box-shadow: 0 30px 80px -30px rgba(129, 140, 248, .45); }
.auth-card h1 { font-family: var(--font-display), sans-serif; font-size: 1.7rem; letter-spacing: -.02em; }
.auth-card .lead { color: var(--muted); margin: 6px 0 24px; font-size: .95rem; overflow-wrap: anywhere; }
.auth-form { display: grid; gap: 16px; }
.fld label { display: block; font-size: .85rem; font-weight: 600; margin-bottom: 6px; color: #d5dbf2; }
.fld input { width: 100%; padding: 13px 14px; border-radius: 12px; border: 1px solid var(--line); background: rgba(255, 255, 255, .05); color: var(--text); font: inherit; outline: none; transition: border-color .2s, box-shadow .2s; }
.fld input:focus { border-color: rgba(94, 234, 212, .7); box-shadow: 0 0 0 4px rgba(94, 234, 212, .14); }
.fld input[aria-invalid="true"] { border-color: #f87171; }
.fld .hint { margin-top: 6px; font-size: .78rem; color: var(--muted); }
.fld .err { margin-top: 6px; font-size: .82rem; color: #fca5a5; }
.pw { position: relative; }
.pw input { padding-right: 76px; }
.pw button { position: absolute; right: 8px; top: 50%; transform: translateY(-50%); padding: 6px 10px; border-radius: 8px; border: 0; background: rgba(255, 255, 255, .08); color: var(--muted); font-size: .78rem; cursor: pointer; }
.alert { padding: 12px 14px; border-radius: 12px; font-size: .9rem; background: rgba(248, 113, 113, .12); border: 1px solid rgba(248, 113, 113, .4); color: #fecaca; }
.alert.ok { background: rgba(94, 234, 212, .12); border-color: rgba(94, 234, 212, .4); color: #99f6e4; }
.auth-submit { width: 100%; padding: 14px; border: 0; border-radius: 14px; font-weight: 700; font-size: 1rem; color: #06101f; cursor: pointer; background: linear-gradient(135deg, var(--accent), var(--accent2)); }
.auth-submit:disabled { opacity: .7; cursor: progress; }
.auth-foot { margin-top: 22px; text-align: center; font-size: .9rem; color: var(--muted); }
.auth-foot a { color: var(--accent); text-decoration: underline; text-underline-offset: 3px; }

@media (max-width: 700px) {
  .nav { display: none; }
  .uname { display: none; }
  .usermenu summary { padding-right: 4px; }
}
'''

# =====================================================================
# Apply
# =====================================================================

problems = []

page_path = FRONT / "app/page.js"
page_text = page_path.read_text(encoding="utf-8")
page_new = page_text
if "BRAND.name" not in page_text:
    if page_text.count("name: 'JobScope',") != 1:
        problems.append("app/page.js: expected exactly one \"name: 'JobScope',\"")
    elif page_text.count("import { TRENDING } from '../lib/trending';") != 1:
        problems.append("app/page.js: TRENDING import line not found")
    else:
        page_new = page_text.replace("name: 'JobScope',", "name: BRAND.name,").replace(
            "import { TRENDING } from '../lib/trending';",
            "import { TRENDING } from '../lib/trending';\nimport { BRAND } from '../lib/brand';",
        )

css_path = FRONT / "app/globals.css"
if not css_path.exists():
    problems.append("app/globals.css not found")

if problems:
    print("Nothing was changed. Problems found:")
    for p in problems:
        print("  -", p)
    sys.exit(1)

written = []
for path, content in FILES.items():
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_name(path.name + ".prepatch")
        if not backup.exists():
            shutil.copy2(path, backup)
    path.write_text(content, encoding="utf-8")
    written.append(str(path))

if page_new != page_text:
    shutil.copy2(page_path, str(page_path) + ".prepatch")
    page_path.write_text(page_new, encoding="utf-8")
    written.append(str(page_path))

css_text = css_path.read_text(encoding="utf-8")
if CSS_MARK not in css_text:
    shutil.copy2(css_path, str(css_path) + ".prepatch")
    with css_path.open("a", encoding="utf-8") as handle:
        handle.write(CSS)
    written.append(str(css_path))

# The default Next.js favicon would override the new logo.
old_icon = FRONT / "app/favicon.ico"
if old_icon.exists():
    old_icon.rename(old_icon.with_name("favicon.ico.prepatch"))

print(f"Installed {len(written)} files:")
for item in written:
    print("  +", item)
print("\nNext: restart the backend and the frontend (see the instructions).")
