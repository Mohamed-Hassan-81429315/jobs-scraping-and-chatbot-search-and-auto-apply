#!/usr/bin/env python3
"""
Replaces "email a reset link" with "email a 6-digit code (OTP)".

Run from the project root:
    python3 install_otp_reset.py
    cd jobs-backend && php artisan migrate && php artisan config:clear

BACKEND   password_reset_otps table, PasswordResetController (forgot + reset), PasswordOtpMail + view
          - code: 6 digits, stored only as an HMAC, valid 10 minutes, max 5 wrong tries, one resend per 60 s
          - the response never reveals whether an email has an account
          - after a reset, every API token of that user is revoked
FRONTEND  /forgot-password (enter email) -> /reset-password (enter code + new password) -> login with a success notice

Existing files that get replaced are backed up as <name>.prepatch.
Your mail settings (including the password) go in jobs-backend/.env only. This script never touches .env.
"""

import pathlib
import shutil
import sys

ROOT = pathlib.Path(".")
BACK = ROOT / "jobs-backend"
FRONT = ROOT / "jobs-frontend"

if not (BACK / "artisan").exists() or not (FRONT / "app").exists():
    sys.exit("Run this from the project root (the folder that contains jobs-backend and jobs-frontend).")

FILES = {}

# =====================================================================
# BACKEND
# =====================================================================

FILES[BACK / "database/migrations/2026_11_24_000000_create_password_reset_otps_table.php"] = r'''<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('password_reset_otps', function (Blueprint $table) {
            $table->string('email')->primary();          // lower-cased; one active code per email
            $table->string('code_hash');                  // HMAC of the code, never the code itself
            $table->unsignedTinyInteger('attempts')->default(0);
            $table->timestamp('expires_at');
            $table->timestamp('last_sent_at');
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('password_reset_otps');
    }
};
'''

FILES[BACK / "app/Mail/PasswordOtpMail.php"] = r'''<?php

namespace App\Mail;

use Illuminate\Bus\Queueable;
use Illuminate\Mail\Mailable;
use Illuminate\Mail\Mailables\Content;
use Illuminate\Mail\Mailables\Envelope;
use Illuminate\Queue\SerializesModels;

class PasswordOtpMail extends Mailable
{
    use Queueable, SerializesModels;

    // Not queued on purpose: the code must not be written into a jobs table.
    public function __construct(public string $code, public int $minutes, public string $name)
    {
    }

    public function envelope(): Envelope
    {
        return new Envelope(subject: '[Applyra] Your password reset verification code');
    }

    public function content(): Content
    {
        return new Content(view: 'emails.password-otp', text: 'emails.password-otp-text');
    }
}
'''

FILES[BACK / "resources/views/emails/password-otp.blade.php"] = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>Your Applyra password reset verification code</title>
</head>
<body style="margin:0;padding:0;background:#f6f8fa;font-family:Arial,Helvetica,sans-serif;color:#1f2328;">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">
    Your Applyra password reset verification code is ready. It expires in {{ $minutes }} minutes.
  </div>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#f6f8fa;">
    <tr>
      <td align="center" style="padding:40px 16px;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:560px;">
          <tr>
            <td align="center" style="padding:0 0 24px;">
              <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <td align="center" valign="middle" width="40" height="40" style="width:40px;height:40px;border-radius:50%;background:#0b6bcb;color:#ffffff;font-size:22px;font-weight:700;">A</td>
                  <td style="padding-left:10px;color:#1f2328;font-size:21px;font-weight:700;letter-spacing:-0.4px;">Applyra</td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:30px 32px;background:#ffffff;border:1px solid #d8dee4;border-radius:12px;">
              <h1 style="margin:0 0 14px;font-size:24px;line-height:1.35;font-weight:600;color:#1f2328;">
                Please verify your identity, {{ $name }}
              </h1>
              <p style="margin:0 0 22px;font-size:15px;line-height:1.6;color:#424a53;">
                We received a request to reset the password for your Applyra account. Use the verification code below to continue.
              </p>
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border:1px solid #d8dee4;border-radius:8px;">
                <tr>
                  <td style="padding:20px 22px 22px;">
                    <p style="margin:0 0 12px;font-size:14px;line-height:1.5;color:#424a53;">
                      Here is your Applyra password reset verification code:
                    </p>
                    <p style="margin:0 0 18px;text-align:center;font-family:'Courier New',Courier,monospace;font-size:32px;line-height:1.4;font-weight:700;letter-spacing:8px;color:#1f2328;">
                      {{ $code }}
                    </p>
                    <p style="margin:0;font-size:14px;line-height:1.6;color:#424a53;">
                      This code is valid for <strong>{{ $minutes }} minutes</strong> and can only be used once.
                    </p>
                  </td>
                </tr>
              </table>
              <p style="margin:20px 0 10px;font-size:14px;line-height:1.6;color:#424a53;">
                <strong>Please don't share this code with anyone.</strong> Applyra will never ask you to provide it by phone or email.
              </p>
              <p style="margin:0;font-size:14px;line-height:1.6;color:#57606a;">
                If you didn't request this code, you can safely ignore this email. Your password will remain unchanged.
              </p>
              <p style="margin:22px 0 0;font-size:14px;line-height:1.6;color:#424a53;">
                Thanks,<br>The Applyra Team
              </p>
            </td>
          </tr>
          <tr>
            <td align="center" style="padding:18px 12px 0;font-size:12px;line-height:1.5;color:#6e7781;">
              This message was sent because a password reset was requested for an Applyra account.
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
'''
FILES[BACK / "resources/views/emails/password-otp-text.blade.php"] = r'''Please verify your identity, {{ $name }}.

We received a request to reset the password for your Applyra account.

Here is your Applyra password reset verification code:
{{ $code }}

This code is valid for {{ $minutes }} minutes and can only be used once.
Please don't share this code with anyone. Applyra will never ask you to provide it by phone or email.

If you didn't request this code, you can safely ignore this email. Your password will remain unchanged.

Thanks,
The Applyra Team
'''

FILES[BACK / "app/Http/Controllers/PasswordResetController.php"] = r'''<?php

namespace App\Http\Controllers;

use App\Mail\PasswordOtpMail;
use App\Models\User;
use Carbon\Carbon;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Mail;
use Illuminate\Validation\Rules\Password as PasswordRule;

class PasswordResetController extends Controller
{
    private const TABLE = 'password_reset_otps';
    private const TTL_MINUTES = 10;
    private const MAX_ATTEMPTS = 5;
    private const RESEND_AFTER_SECONDS = 60;

    /** Step 1: email a 6-digit code. Always answers the same, so emails cannot be probed. */
    public function forgot(Request $request): JsonResponse
    {
        $data = $request->validate(['email' => ['required', 'email', 'max:255']]);
        $email = strtolower(trim($data['email']));

        $user = User::whereRaw('lower(email) = ?', [$email])->first();
        if ($user) {
            $this->issueCode($user);
        }

        return response()->json(['message' => 'If that email has an account, a 6-digit code is on its way.']);
    }

    /** Step 2: code + new password. */
    public function reset(Request $request): JsonResponse
    {
        $data = $request->validate([
            'email' => ['required', 'email', 'max:255'],
            'code' => ['required', 'digits:6'],
            'password' => ['required', 'confirmed', PasswordRule::min(8)->letters()->numbers()],
        ]);
        $email = strtolower(trim($data['email']));

        $invalid = fn () => response()->json([
            'message' => 'That code is invalid or has expired.',
            'errors' => ['code' => ['That code is invalid or has expired.']],
        ], 422);

        $row = DB::table(self::TABLE)->where('email', $email)->first();

        if (
            !$row
            || Carbon::parse($row->expires_at)->isPast()
            || $row->attempts >= self::MAX_ATTEMPTS
        ) {
            return $invalid();
        }

        if (!hash_equals($row->code_hash, $this->hashCode($email, $data['code']))) {
            DB::table(self::TABLE)->where('email', $email)->increment('attempts');

            return $invalid();
        }

        $user = User::whereRaw('lower(email) = ?', [$email])->first();
        if (!$user) {
            DB::table(self::TABLE)->where('email', $email)->delete();

            return $invalid();
        }

        DB::transaction(function () use ($user, $email, $data) {
            $user->forceFill(['password' => Hash::make($data['password'])])->save();

            if (method_exists($user, 'tokens')) {
                $user->tokens()->delete(); // sign the user out everywhere
            }

            DB::table(self::TABLE)->where('email', $email)->delete(); // a code works once
        });

        return response()->json(['message' => 'Your password has been reset.']);
    }

    private function issueCode(User $user): void
    {
        $key = strtolower($user->email);
        $row = DB::table(self::TABLE)->where('email', $key)->first();

        // Resend cooldown: quietly do nothing if a code was sent a moment ago.
        if ($row && Carbon::parse($row->last_sent_at)->gt(now()->subSeconds(self::RESEND_AFTER_SECONDS))) {
            return;
        }

        $code = str_pad((string) random_int(0, 999999), 6, '0', STR_PAD_LEFT);

        DB::table(self::TABLE)->updateOrInsert(['email' => $key], [
            'code_hash' => $this->hashCode($key, $code),
            'attempts' => 0,
            'expires_at' => now()->addMinutes(self::TTL_MINUTES),
            'last_sent_at' => now(),
            'created_at' => $row->created_at ?? now(),
            'updated_at' => now(),
        ]);

        try {
            Mail::to($user->email)->send(new PasswordOtpMail($code, self::TTL_MINUTES, $user->name ?: 'there'));
        } catch (\Throwable $e) {
            Log::error('Password reset code email failed: ' . $e->getMessage());
            DB::table(self::TABLE)->where('email', $key)->delete(); // do not lock the user in the cooldown
        }
    }

    /** Keyed hash: a leaked table cannot be reversed by trying all 1,000,000 codes without the app key. */
    private function hashCode(string $email, string $code): string
    {
        return hash_hmac('sha256', $email . '|' . $code, (string) config('app.key'));
    }
}
'''

# =====================================================================
# FRONTEND
# =====================================================================

FILES[FRONT / "app/auth/otp-actions.js"] = r'''"use server";

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
'''

FILES[FRONT / "components/auth/ForgotOtpForm.js"] = r'''"use client";

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
'''

FILES[FRONT / "components/auth/ResetOtpForm.js"] = r'''"use client";

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
'''

FILES[FRONT / "app/forgot-password/page.js"] = r'''import Link from 'next/link';
import { redirect } from 'next/navigation';
import { getUser } from '../../lib/auth';
import AuthShell from '../../components/auth/AuthShell';
import ForgotOtpForm from '../../components/auth/ForgotOtpForm';

export const metadata = {
  title: 'Reset your password',
  description: 'Get a 6-digit code by email to reset your password.',
  robots: { index: false, follow: false },
  alternates: { canonical: '/forgot-password' },
};

export default async function ForgotPasswordPage() {
  if (await getUser()) redirect('/');

  return (
    <AuthShell
      title="Reset your password"
      lead="Enter your email and we will send you a 6-digit code."
      footer={<Link href="/" prefetch={false}>Back to sign in</Link>}
    >
      <ForgotOtpForm />
    </AuthShell>
  );
}
'''

FILES[FRONT / "app/reset-password/page.js"] = r'''import Link from 'next/link';
import { redirect } from 'next/navigation';
import { getUser } from '../../lib/auth';
import { resendOtpAction } from '../auth/otp-actions';
import AuthShell from '../../components/auth/AuthShell';
import ResetOtpForm from '../../components/auth/ResetOtpForm';

export const metadata = {
  title: 'Enter your code',
  description: 'Enter the 6-digit code from your email and choose a new password.',
  robots: { index: false, follow: false },
  alternates: { canonical: '/reset-password' },
};

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default async function ResetPasswordPage({ searchParams }) {
  if (await getUser()) redirect('/');

  const sp = await searchParams;
  const email = String(sp?.email ?? '').trim().toLowerCase();
  if (!EMAIL.test(email)) redirect('/forgot-password');

  return (
    <AuthShell
      title="Enter your code"
      lead={`If ${email} has an account, we sent it a 6-digit code. It expires in 10 minutes.`}
      footer={<Link href="/" prefetch={false}>Back to sign in</Link>}
    >
      <ResetOtpForm email={email} />
      <form action={resendOtpAction} className="auth-forgot">
        <input type="hidden" name="email" value={email} />
        <button type="submit" className="btn-link">Resend code</button>
      </form>
    </AuthShell>
  );
}
'''

# =====================================================================
# write
# =====================================================================


def backup(path):
    bak = path.with_name(path.name + ".prepatch")
    if path.exists() and not bak.exists():
        shutil.copy2(path, bak)


for path, content in FILES.items():
    backup(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"wrote    {path}")

# --- make sure the two API routes exist -------------------------------
api_routes = BACK / "routes/api.php"
ROUTES = r'''

use App\Http\Controllers\PasswordResetController;

Route::prefix('auth')->middleware('throttle:5,1')->group(function () {
    Route::post('/forgot-password', [PasswordResetController::class, 'forgot']);
    Route::post('/reset-password', [PasswordResetController::class, 'reset']);
});
'''
if api_routes.exists():
    text = api_routes.read_text(encoding="utf-8")
    if "forgot-password" in text and "PasswordResetController" in text:
        print("routes   already present in routes/api.php")
    elif "forgot-password" in text:
        print("WARNING  routes/api.php already has a forgot-password route that uses a different controller.")
        print("         Point /auth/forgot-password and /auth/reset-password at PasswordResetController@forgot / @reset.")
    else:
        backup(api_routes)
        api_routes.write_text(text.rstrip() + "\n" + ROUTES, encoding="utf-8")
        print(f"patched  {api_routes}")
else:
    print("WARNING  routes/api.php not found: add the two POST routes by hand (see the script).")

print("""
Done. Next:

1) jobs-backend/.env  (use YOUR values; the password is a NEW Google app password, no spaces)

   APP_NAME="HireLuMe"
   MAIL_MAILER=smtp
   MAIL_HOST=smtp.gmail.com
   MAIL_PORT=587
   MAIL_SCHEME=smtp
   MAIL_USERNAME=your.gmail.address@gmail.com
   MAIL_PASSWORD=your-new-16-character-app-password
   MAIL_FROM_ADDRESS=your.gmail.address@gmail.com
   MAIL_FROM_NAME="HireLuMe"

   (Laravel 10 or older: use MAIL_ENCRYPTION=tls instead of MAIL_SCHEME.)

2) cd jobs-backend && php artisan migrate && php artisan config:clear && php artisan route:clear
""")
