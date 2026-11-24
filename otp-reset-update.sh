#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f "jobs-backend/artisan" || ! -d "jobs-frontend/app" ]]; then
  echo "Error: run this command from the Applyra project root (the folder containing jobs-backend and jobs-frontend)." >&2
  exit 1
fi

installer_tmp="$(mktemp "${TMPDIR:-/tmp}/applyra-otp-installer.XXXXXX.py")"
trap 'rm -f "$installer_tmp"' EXIT
cat > "$installer_tmp" <<'APPLYRA_OTP_INSTALLER_EOF'
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

import base64
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
                  <td align="center" valign="middle" width="40" height="40" style="width:40px;height:40px;">
                    <img src="{{ $message->embed(public_path('images/applyra-logo.png')) }}" width="40" height="40" alt="Applyra logo" style="display:block;width:40px;height:40px;border:0;border-radius:10px;">
                  </td>
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

FILES[BACK / "tests/Feature/PasswordOtpMailTest.php"] = r'''<?php

namespace Tests\Feature;

use App\Mail\PasswordOtpMail;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Mail;
use Tests\TestCase;

class PasswordOtpMailTest extends TestCase
{
    use RefreshDatabase;

    public function test_forgot_password_sends_a_branded_single_use_code_email(): void
    {
        Mail::fake();
        $user = User::factory()->create([
            'name' => 'Sara Ali',
            'email' => 'sara@example.com',
        ]);

        $this->postJson('/api/auth/forgot-password', ['email' => $user->email])
            ->assertOk()
            ->assertJsonPath('message', 'If that email has an account, a 6-digit code is on its way.');

        Mail::assertSent(PasswordOtpMail::class, function (PasswordOtpMail $mail) use ($user): bool {
            $html = $mail->render();
            $text = view('emails.password-otp-text', [
                'code' => $mail->code,
                'minutes' => $mail->minutes,
                'name' => $mail->name,
            ])->render();

            return $mail->hasTo($user->email)
                && $mail->name === 'Sara Ali'
                && $mail->minutes === 10
                && preg_match('/^\d{6}$/', $mail->code) === 1
                && str_contains($html, 'Applyra logo')
                && preg_match('/src="cid:[^"]+"/', $html) === 1
                && str_contains($html, 'Please verify your identity, Sara Ali')
                && str_contains($html, 'Here is your Applyra password reset verification code:')
                && str_contains($html, 'This code is valid for')
                && str_contains($text, $mail->code);
        });
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
const clean = (value) => String(value ?? '').trim();
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

/** Request a code without navigating; the client shows its confirmation dialog. */
export async function requestOtpAction(_prev, formData) {
  const email = clean(formData.get('email')).toLowerCase();
  const values = { email };
  if (!EMAIL.test(email)) return state({ errors: { email: 'Enter a valid email address.' }, values });

  const res = await api('/auth/forgot-password', { method: 'POST', body: { email } });
  if (!res.ok) return failure(res, values);

  return state({ email, sentAt: Date.now(), success: 'code-requested', values });
}

/** Resend a code; the backend remains authoritative for its one-minute cooldown. */
export async function resendOtpAction(_prev, formData) {
  const email = clean(formData.get('email')).toLowerCase();
  const values = { email };
  if (!EMAIL.test(email)) return state({ errors: { email: 'Enter a valid email address.' }, values });

  const res = await api('/auth/forgot-password', { method: 'POST', body: { email } });
  if (!res.ok) return failure(res, values);

  return state({ email, sentAt: Date.now(), success: 'resend-requested', values });
}

/** Reset form: code + new password. On success the user signs in again with the new password. */
export async function resetWithOtpAction(_prev, formData) {
  const email = clean(formData.get('email')).toLowerCase();
  const code = clean(formData.get('code')).replace(/\D/g, '').slice(0, 6);
  const password = String(formData.get('password') ?? '');
  const password_confirmation = String(formData.get('password_confirmation') ?? '');
  const values = { code };

  if (!EMAIL.test(email)) return state({ errors: { email: 'Enter a valid email address.' }, values });
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
import OtpSentDialog from './OtpSentDialog';

const INITIAL = { errors: {}, error: '', success: '', values: {} };

export default function ForgotOtpForm() {
  const [state, action] = useActionState(requestOtpAction, INITIAL);

  return (
    <>
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
      {state.email && state.sentAt ? <OtpSentDialog email={state.email} sentAt={state.sentAt} /> : null}
    </>
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
import AuthShell from '../../components/auth/AuthShell';
import ResetOtpForm from '../../components/auth/ResetOtpForm';
import ResendCodeControl from '../../components/auth/ResendCodeControl';

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

  const requestedAt = Number(sp?.sentAt ?? 0);
  const sentAt = Number.isSafeInteger(requestedAt) && requestedAt > 0 && requestedAt < 4_102_444_800_000
    ? requestedAt
    : 0;

  return (
    <AuthShell
      title="Enter your code"
      lead={`If ${email} has an account, we sent it a 6-digit code. It expires in 10 minutes.`}
      footer={<Link href="/" prefetch={false}>Back to sign in</Link>}
    >
      <ResetOtpForm email={email} />
      <ResendCodeControl email={email} initialSentAt={sentAt} />
    </AuthShell>
  );
}
'''

FILES[FRONT / "components/auth/OtpSentDialog.js"] = r'''"use client";

import { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import ResendCodeControl from './ResendCodeControl';
import styles from './OtpSentDialog.module.css';

export default function OtpSentDialog({ email, sentAt }) {
  const router = useRouter();
  const dialogRef = useRef(null);
  const latestSentAtRef = useRef(sentAt);
  const [dismissedSentAt, setDismissedSentAt] = useState(0);
  const isOpen = Boolean(email && sentAt && dismissedSentAt !== sentAt);

  useEffect(() => {
    latestSentAtRef.current = sentAt;
  }, [sentAt]);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (isOpen && !dialog.open) dialog.showModal();
    if (!isOpen && dialog.open) dialog.close();
  }, [isOpen]);

  const handleResent = useCallback((timestamp) => {
    latestSentAtRef.current = timestamp;
  }, []);

  function continueToCodeEntry() {
    setDismissedSentAt(sentAt);
    const params = new URLSearchParams({ email, sentAt: String(latestSentAtRef.current || sentAt) });
    router.push(`/reset-password?${params.toString()}`);
  }

  if (!email || !sentAt) return null;

  return (
    <dialog
      ref={dialogRef}
      className={styles.dialog}
      aria-labelledby="otp-sent-title"
      aria-describedby="otp-sent-description"
      onClose={() => setDismissedSentAt(sentAt)}
      onClick={(event) => {
        if (event.target === dialogRef.current) setDismissedSentAt(sentAt);
      }}
    >
      <section className={styles.card}>
        <button
          type="button"
          className={styles.close}
          aria-label="Close confirmation"
          onClick={() => setDismissedSentAt(sentAt)}
        >
          <svg viewBox="0 0 20 20" aria-hidden="true"><path d="m5 5 10 10M15 5 5 15" /></svg>
        </button>

        <div className={styles.mailIcon} aria-hidden="true">
          <svg viewBox="0 0 48 48"><rect x="6" y="10" width="36" height="28" rx="6" /><path d="m8 14 16 12 16-12" /></svg>
        </div>

        <p className={styles.eyebrow}>Code requested</p>
        <h2 id="otp-sent-title" className={styles.title}>Check your email</h2>
        <div className={styles.notice}>
          <p className={styles.noticeLabel}>OTP code requested for</p>
          <p className={styles.email}>{email}</p>
        </div>
        <p id="otp-sent-description" className={styles.description}>
          If an Applyra account exists for this address, a verification code is on its way. Check your inbox and spam folder now. If you do not receive a code, use Resend Code below after the one-minute cooldown.
        </p>

        <ResendCodeControl
          email={email}
          initialSentAt={sentAt}
          onResent={handleResent}
          variant="dialog"
        />

        <button type="button" className={styles.confirm} onClick={continueToCodeEntry}>
          OK, Received It
          <span aria-hidden="true">→</span>
        </button>
      </section>
    </dialog>
  );
}
'''

FILES[FRONT / "components/auth/ResendCodeControl.js"] = r'''"use client";

import { useActionState, useEffect, useState } from 'react';
import { resendOtpAction } from '../../app/auth/otp-actions';
import styles from './OtpSentDialog.module.css';

const INITIAL = { errors: {}, error: '', success: '', values: {} };
const RESEND_WAIT_MS = 60_000;

function formatCountdown(totalSeconds) {
  const minutes = Math.floor(totalSeconds / 60).toString().padStart(2, '0');
  const seconds = (totalSeconds % 60).toString().padStart(2, '0');
  return `${minutes}:${seconds}`;
}

export default function ResendCodeControl({ email, initialSentAt = 0, onResent, variant = 'page' }) {
  const [state, action, pending] = useActionState(resendOtpAction, INITIAL);
  const [now, setNow] = useState(0);
  const latestSentAt = Number(state.sentAt) || Number(initialSentAt) || 0;
  const deadline = latestSentAt > 0 ? latestSentAt + RESEND_WAIT_MS : 0;
  const remaining = deadline
    ? Math.max(0, Math.ceil((deadline - (now || deadline - RESEND_WAIT_MS)) / 1000))
    : 0;

  useEffect(() => {
    if (!state.sentAt) return;
    onResent?.(Number(state.sentAt));
  }, [state.sentAt, onResent]);

  useEffect(() => {
    if (!deadline) {
      return undefined;
    }

    let timer;
    const tick = () => {
      const timestamp = Date.now();
      setNow(timestamp);
      if (timestamp < deadline) {
        timer = window.setTimeout(tick, Math.min(1000, deadline - timestamp));
      }
    };
    timer = window.setTimeout(tick, 0);
    return () => {
      window.clearTimeout(timer);
    };
  }, [deadline]);

  const isDialog = variant === 'dialog';
  const disabled = pending || remaining > 0;

  return (
    <div className={`${styles.resend} ${isDialog ? styles.resendDialog : ''}`}>
      <form action={action}>
        <input type="hidden" name="email" value={email} />
        <button type="submit" className={styles.resendButton} disabled={disabled}>
          {pending ? (
            <><span className={styles.spinner} aria-hidden="true" /> Sending code…</>
          ) : 'Resend Code'}
        </button>
      </form>
      {remaining > 0 ? (
        <p className={styles.cooldown} role="status" aria-live="polite">
          You can request another code in <strong>{formatCountdown(remaining)}</strong>.
        </p>
      ) : null}
      {state.error ? <p className={styles.error} role="alert">{state.error}</p> : null}
      {state.success === 'resend-requested' ? (
        <p className={styles.resendSuccess} role="status" aria-live="polite">
          If an account exists for this email, a new code is on its way.
        </p>
      ) : null}
    </div>
  );
}
'''

FILES[FRONT / "components/auth/OtpSentDialog.module.css"] = r'''.dialog {
  width: min(100% - 28px, 470px);
  max-width: 470px;
  max-height: min(90dvh, 760px);
  padding: 0;
  overflow: auto;
  border: 1px solid rgba(148, 163, 184, .3);
  border-radius: 24px;
  color: #eef1fb;
  background: #10172d;
  box-shadow: 0 32px 100px rgba(0, 0, 0, .55), 0 0 0 1px rgba(129, 140, 248, .08);
  overscroll-behavior: contain;
}

.dialog[open] {
  animation: otp-dialog-in 320ms cubic-bezier(.2, .8, .2, 1) both;
}

.dialog::backdrop {
  background: rgba(3, 7, 18, .72);
  backdrop-filter: blur(7px);
  animation: otp-backdrop-in 220ms ease-out both;
}

.card {
  position: relative;
  padding: 34px 30px 28px;
}

.close {
  position: absolute;
  top: 15px;
  right: 15px;
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, .12);
  border-radius: 50%;
  color: #c5cce0;
  background: rgba(255, 255, 255, .05);
  cursor: pointer;
  transition: background 160ms ease, color 160ms ease, transform 160ms ease;
}

.close:hover { color: #fff; background: rgba(255, 255, 255, .12); transform: rotate(5deg); }
.close svg { width: 17px; height: 17px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; }

.mailIcon {
  display: grid;
  width: 58px;
  height: 58px;
  place-items: center;
  margin-bottom: 18px;
  border: 1px solid rgba(94, 234, 212, .26);
  border-radius: 18px;
  color: #07121d;
  background: linear-gradient(135deg, #5eead4, #818cf8);
  box-shadow: 0 12px 34px rgba(94, 234, 212, .18);
  animation: otp-icon-pulse 2.6s ease-in-out 400ms infinite;
}

.mailIcon svg { width: 34px; height: 34px; fill: none; stroke: currentColor; stroke-width: 2.3; stroke-linecap: round; stroke-linejoin: round; }
.eyebrow { margin-bottom: 5px; color: #78e5d4; font-size: .76rem; font-weight: 700; letter-spacing: .13em; text-transform: uppercase; }
.title { margin: 0 36px 16px 0; color: #f4f6ff; font-size: clamp(1.45rem, 5vw, 1.85rem); line-height: 1.2; letter-spacing: -.025em; }

.notice {
  margin-bottom: 16px;
  padding: 14px 16px;
  border: 1px solid rgba(11, 107, 203, .1);
  border-radius: 15px;
  color: #263342;
  background: #eef5fa;
  box-shadow: inset 0 1px rgba(255, 255, 255, .75);
}

.noticeLabel { margin-bottom: 5px; color: #536373; font-size: .8rem; font-weight: 600; }
.email { overflow-wrap: anywhere; color: #10293d; font-size: 1rem; font-weight: 700; }
.description { margin: 0 0 18px; color: #b4bdd5; font-size: .9rem; line-height: 1.65; }

.resend {
  display: grid;
  gap: 8px;
  margin: 2px 0 20px;
}
.resendDialog { margin-top: 2px; }
.resend form { margin: 0; }
.resendButton {
  display: inline-flex;
  min-height: 42px;
  align-items: center;
  justify-content: center;
  gap: 9px;
  padding: 0 18px;
  border: 1px solid rgba(129, 140, 248, .45);
  border-radius: 999px;
  color: #e2e7ff;
  background: rgba(129, 140, 248, .12);
  font-size: .9rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 160ms ease, border-color 160ms ease, transform 160ms ease, opacity 160ms ease;
}
.resendButton:not(:disabled):hover { transform: translateY(-1px); border-color: rgba(129, 140, 248, .8); background: rgba(129, 140, 248, .22); }
.resendButton:disabled { cursor: not-allowed; opacity: .62; }
.cooldown, .resendSuccess { color: #aeb8d2; font-size: .8rem; line-height: 1.5; }
.cooldown strong { color: #eef1fb; font-variant-numeric: tabular-nums; }
.error { color: #fda4af; font-size: .82rem; line-height: 1.5; }
.resendSuccess { color: #7ee7d6; }

.spinner {
  width: 15px;
  height: 15px;
  border: 2px solid rgba(226, 231, 255, .35);
  border-top-color: #e2e7ff;
  border-radius: 50%;
  animation: otp-spin 700ms linear infinite;
}

.confirm {
  display: flex;
  width: 100%;
  min-height: 48px;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 12px 18px;
  border: 0;
  border-radius: 14px;
  color: #07121d;
  background: linear-gradient(110deg, #5eead4, #818cf8);
  box-shadow: 0 12px 28px rgba(94, 234, 212, .16);
  font-size: .96rem;
  font-weight: 800;
  cursor: pointer;
  transition: transform 160ms ease, box-shadow 160ms ease, filter 160ms ease;
}
.confirm span { font-size: 1.2rem; line-height: 1; transition: transform 160ms ease; }
.confirm:hover { transform: translateY(-1px); box-shadow: 0 16px 34px rgba(94, 234, 212, .25); filter: saturate(1.08); }
.confirm:hover span { transform: translateX(3px); }
.confirm:active { transform: translateY(0); }

@keyframes otp-dialog-in {
  from { opacity: 0; transform: translateY(14px) scale(.97); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
@keyframes otp-backdrop-in { from { opacity: 0; } to { opacity: 1; } }
@keyframes otp-icon-pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.045); } }
@keyframes otp-spin { to { transform: rotate(360deg); } }

@media (max-width: 520px) {
  .card { padding: 30px 20px 22px; }
  .dialog { border-radius: 20px; }
}

@media (prefers-reduced-motion: reduce) {
  .dialog[open], .dialog::backdrop, .mailIcon, .spinner { animation: none; }
  .close, .resendButton, .confirm, .confirm span { transition: none; }
}
'''

ASSETS = {
    BACK / "public/images/applyra-logo.png": base64.b64decode(
        "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"
    ),
}

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

for path, content in ASSETS.items():
    backup(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
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
   APP_NAME="Applyra"
   MAIL_MAILER=smtp
   MAIL_HOST=smtp.gmail.com
   MAIL_PORT=587
   MAIL_SCHEME=smtp
   MAIL_USERNAME=your.gmail.address@gmail.com
   MAIL_PASSWORD=your-new-16-character-app-password
   MAIL_FROM_ADDRESS=your.gmail.address@gmail.com
   MAIL_FROM_NAME="Applyra"

   (Laravel 10 or older: use MAIL_ENCRYPTION=tls instead of MAIL_SCHEME.)

2) cd jobs-backend && php artisan migrate && php artisan config:clear && php artisan route:clear
""")
APPLYRA_OTP_INSTALLER_EOF
python3 "$installer_tmp"
