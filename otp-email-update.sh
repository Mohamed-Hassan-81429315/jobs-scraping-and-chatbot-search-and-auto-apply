#!/usr/bin/env bash
set -euo pipefail

# Apply the Applyra OTP verification email update from the repository root.
if [[ ! -f jobs-backend/artisan || ! -d jobs-frontend/app ]]; then
  echo "Run this command from the project root (the directory containing jobs-backend/ and jobs-frontend/)." >&2
  exit 2
fi

# Make repeat runs harmless and avoid attempting to reapply the diff.
if grep -qF '[Applyra] Your password reset verification code' jobs-backend/app/Mail/PasswordOtpMail.php \
  && grep -qF 'Please verify your identity' jobs-backend/resources/views/emails/password-otp.blade.php \
  && grep -qF 'password-otp-text' jobs-backend/app/Mail/PasswordOtpMail.php \
  && [[ -f jobs-backend/resources/views/emails/password-otp-text.blade.php ]] \
  && [[ -f jobs-backend/tests/Feature/PasswordOtpMailTest.php ]]; then
  echo "Applyra OTP email update is already present; no files changed."
  exit 0
fi

patch_file="$(mktemp)"
trap 'rm -f "$patch_file"' EXIT
cat > "$patch_file" <<'OTP_EMAIL_PATCH'
diff --git a/install_otp_reset.py b/install_otp_reset.py
index 178f934..6c419ff 100644
--- a/install_otp_reset.py
+++ b/install_otp_reset.py
@@ -75,37 +75,109 @@ class PasswordOtpMail extends Mailable
     use Queueable, SerializesModels;
 
     // Not queued on purpose: the code must not be written into a jobs table.
-    public function __construct(public string $code, public int $minutes)
+    public function __construct(public string $code, public int $minutes, public string $name)
     {
     }
 
     public function envelope(): Envelope
     {
-        return new Envelope(subject: 'Your password reset code');
+        return new Envelope(subject: '[Applyra] Your password reset verification code');
     }
 
     public function content(): Content
     {
-        return new Content(view: 'emails.password-otp');
+        return new Content(view: 'emails.password-otp', text: 'emails.password-otp-text');
     }
 }
 '''
 
 FILES[BACK / "resources/views/emails/password-otp.blade.php"] = r'''<!doctype html>
-<html>
-<body style="margin:0;padding:24px;background:#f4f6fb;font-family:Arial,Helvetica,sans-serif;color:#111827;">
-  <div style="max-width:460px;margin:0 auto;background:#ffffff;border-radius:14px;padding:28px;">
-    <h2 style="margin:0 0 8px;font-size:20px;">Your password reset code</h2>
-    <p style="margin:0 0 4px;color:#374151;">Use this code to choose a new password on {{ config('app.name') }}:</p>
-    <p style="margin:18px 0;font-size:36px;letter-spacing:10px;font-weight:700;">{{ $code }}</p>
-    <p style="margin:0;color:#6b7280;font-size:14px;line-height:1.5;">
-      It expires in {{ $minutes }} minutes. If you did not ask for it, ignore this email: your password stays the same.
-      Never share this code with anyone.
-    </p>
+<html lang="en">
+<head>
+  <meta charset="utf-8">
+  <meta name="viewport" content="width=device-width, initial-scale=1">
+  <meta name="color-scheme" content="light">
+  <title>Your Applyra password reset verification code</title>
+</head>
+<body style="margin:0;padding:0;background:#f6f8fa;font-family:Arial,Helvetica,sans-serif;color:#1f2328;">
+  <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">
+    Your Applyra password reset verification code is ready. It expires in {{ $minutes }} minutes.
   </div>
+  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#f6f8fa;">
+    <tr>
+      <td align="center" style="padding:40px 16px;">
+        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:560px;">
+          <tr>
+            <td align="center" style="padding:0 0 24px;">
+              <table role="presentation" cellspacing="0" cellpadding="0" border="0">
+                <tr>
+                  <td align="center" valign="middle" width="40" height="40" style="width:40px;height:40px;border-radius:50%;background:#0b6bcb;color:#ffffff;font-size:22px;font-weight:700;">A</td>
+                  <td style="padding-left:10px;color:#1f2328;font-size:21px;font-weight:700;letter-spacing:-0.4px;">Applyra</td>
+                </tr>
+              </table>
+            </td>
+          </tr>
+          <tr>
+            <td style="padding:30px 32px;background:#ffffff;border:1px solid #d8dee4;border-radius:12px;">
+              <h1 style="margin:0 0 14px;font-size:24px;line-height:1.35;font-weight:600;color:#1f2328;">
+                Please verify your identity, {{ $name }}
+              </h1>
+              <p style="margin:0 0 22px;font-size:15px;line-height:1.6;color:#424a53;">
+                We received a request to reset the password for your Applyra account. Use the verification code below to continue.
+              </p>
+              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border:1px solid #d8dee4;border-radius:8px;">
+                <tr>
+                  <td style="padding:20px 22px 22px;">
+                    <p style="margin:0 0 12px;font-size:14px;line-height:1.5;color:#424a53;">
+                      Here is your Applyra password reset verification code:
+                    </p>
+                    <p style="margin:0 0 18px;text-align:center;font-family:'Courier New',Courier,monospace;font-size:32px;line-height:1.4;font-weight:700;letter-spacing:8px;color:#1f2328;">
+                      {{ $code }}
+                    </p>
+                    <p style="margin:0;font-size:14px;line-height:1.6;color:#424a53;">
+                      This code is valid for <strong>{{ $minutes }} minutes</strong> and can only be used once.
+                    </p>
+                  </td>
+                </tr>
+              </table>
+              <p style="margin:20px 0 10px;font-size:14px;line-height:1.6;color:#424a53;">
+                <strong>Please don't share this code with anyone.</strong> Applyra will never ask you to provide it by phone or email.
+              </p>
+              <p style="margin:0;font-size:14px;line-height:1.6;color:#57606a;">
+                If you didn't request this code, you can safely ignore this email. Your password will remain unchanged.
+              </p>
+              <p style="margin:22px 0 0;font-size:14px;line-height:1.6;color:#424a53;">
+                Thanks,<br>The Applyra Team
+              </p>
+            </td>
+          </tr>
+          <tr>
+            <td align="center" style="padding:18px 12px 0;font-size:12px;line-height:1.5;color:#6e7781;">
+              This message was sent because a password reset was requested for an Applyra account.
+            </td>
+          </tr>
+        </table>
+      </td>
+    </tr>
+  </table>
 </body>
 </html>
 '''
+FILES[BACK / "resources/views/emails/password-otp-text.blade.php"] = r'''Please verify your identity, {{ $name }}.
+
+We received a request to reset the password for your Applyra account.
+
+Here is your Applyra password reset verification code:
+{{ $code }}
+
+This code is valid for {{ $minutes }} minutes and can only be used once.
+Please don't share this code with anyone. Applyra will never ask you to provide it by phone or email.
+
+If you didn't request this code, you can safely ignore this email. Your password will remain unchanged.
+
+Thanks,
+The Applyra Team
+'''
 
 FILES[BACK / "app/Http/Controllers/PasswordResetController.php"] = r'''<?php
 
@@ -216,7 +288,7 @@ class PasswordResetController extends Controller
         ]);
 
         try {
-            Mail::to($user->email)->send(new PasswordOtpMail($code, self::TTL_MINUTES));
+            Mail::to($user->email)->send(new PasswordOtpMail($code, self::TTL_MINUTES, $user->name ?: 'there'));
         } catch (\Throwable $e) {
             Log::error('Password reset code email failed: ' . $e->getMessage());
             DB::table(self::TABLE)->where('email', $key)->delete(); // do not lock the user in the cooldown
diff --git a/jobs-backend/app/Http/Controllers/PasswordResetController.php b/jobs-backend/app/Http/Controllers/PasswordResetController.php
index bbcacb6..682ef23 100644
--- a/jobs-backend/app/Http/Controllers/PasswordResetController.php
+++ b/jobs-backend/app/Http/Controllers/PasswordResetController.php
@@ -107,7 +107,7 @@ private function issueCode(User $user): void
         ]);
 
         try {
-            Mail::to($user->email)->send(new PasswordOtpMail($code, self::TTL_MINUTES));
+            Mail::to($user->email)->send(new PasswordOtpMail($code, self::TTL_MINUTES, $user->name ?: 'there'));
         } catch (\Throwable $e) {
             Log::error('Password reset code email failed: ' . $e->getMessage());
             DB::table(self::TABLE)->where('email', $key)->delete(); // do not lock the user in the cooldown
diff --git a/jobs-backend/app/Mail/PasswordOtpMail.php b/jobs-backend/app/Mail/PasswordOtpMail.php
index b758e6f..2f5e684 100644
--- a/jobs-backend/app/Mail/PasswordOtpMail.php
+++ b/jobs-backend/app/Mail/PasswordOtpMail.php
@@ -13,17 +13,17 @@ class PasswordOtpMail extends Mailable
     use Queueable, SerializesModels;
 
     // Not queued on purpose: the code must not be written into a jobs table.
-    public function __construct(public string $code, public int $minutes)
+    public function __construct(public string $code, public int $minutes, public string $name)
     {
     }
 
     public function envelope(): Envelope
     {
-        return new Envelope(subject: 'Your password reset code');
+        return new Envelope(subject: '[Applyra] Your password reset verification code');
     }
 
     public function content(): Content
     {
-        return new Content(view: 'emails.password-otp');
+        return new Content(view: 'emails.password-otp', text: 'emails.password-otp-text');
     }
 }
diff --git a/jobs-backend/resources/views/emails/password-otp-text.blade.php b/jobs-backend/resources/views/emails/password-otp-text.blade.php
new file mode 100644
index 0000000..d0ee396
--- /dev/null
+++ b/jobs-backend/resources/views/emails/password-otp-text.blade.php
@@ -0,0 +1,14 @@
+Please verify your identity, {{ $name }}.
+
+We received a request to reset the password for your Applyra account.
+
+Here is your Applyra password reset verification code:
+{{ $code }}
+
+This code is valid for {{ $minutes }} minutes and can only be used once.
+Please don't share this code with anyone. Applyra will never ask you to provide it by phone or email.
+
+If you didn't request this code, you can safely ignore this email. Your password will remain unchanged.
+
+Thanks,
+The Applyra Team
diff --git a/jobs-backend/resources/views/emails/password-otp.blade.php b/jobs-backend/resources/views/emails/password-otp.blade.php
index 4f842d4..1d10913 100644
--- a/jobs-backend/resources/views/emails/password-otp.blade.php
+++ b/jobs-backend/resources/views/emails/password-otp.blade.php
@@ -1,14 +1,71 @@
 <!doctype html>
-<html>
-<body style="margin:0;padding:24px;background:#f4f6fb;font-family:Arial,Helvetica,sans-serif;color:#111827;">
-  <div style="max-width:460px;margin:0 auto;background:#ffffff;border-radius:14px;padding:28px;">
-    <h2 style="margin:0 0 8px;font-size:20px;">Your password reset code</h2>
-    <p style="margin:0 0 4px;color:#374151;">Use this code to choose a new password on {{ config('app.name') }}:</p>
-    <p style="margin:18px 0;font-size:36px;letter-spacing:10px;font-weight:700;">{{ $code }}</p>
-    <p style="margin:0;color:#6b7280;font-size:14px;line-height:1.5;">
-      It expires in {{ $minutes }} minutes. If you did not ask for it, ignore this email: your password stays the same.
-      Never share this code with anyone.
-    </p>
+<html lang="en">
+<head>
+  <meta charset="utf-8">
+  <meta name="viewport" content="width=device-width, initial-scale=1">
+  <meta name="color-scheme" content="light">
+  <title>Your Applyra password reset verification code</title>
+</head>
+<body style="margin:0;padding:0;background:#f6f8fa;font-family:Arial,Helvetica,sans-serif;color:#1f2328;">
+  <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">
+    Your Applyra password reset verification code is ready. It expires in {{ $minutes }} minutes.
   </div>
+  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#f6f8fa;">
+    <tr>
+      <td align="center" style="padding:40px 16px;">
+        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:560px;">
+          <tr>
+            <td align="center" style="padding:0 0 24px;">
+              <table role="presentation" cellspacing="0" cellpadding="0" border="0">
+                <tr>
+                  <td align="center" valign="middle" width="40" height="40" style="width:40px;height:40px;border-radius:50%;background:#0b6bcb;color:#ffffff;font-size:22px;font-weight:700;">A</td>
+                  <td style="padding-left:10px;color:#1f2328;font-size:21px;font-weight:700;letter-spacing:-0.4px;">Applyra</td>
+                </tr>
+              </table>
+            </td>
+          </tr>
+          <tr>
+            <td style="padding:30px 32px;background:#ffffff;border:1px solid #d8dee4;border-radius:12px;">
+              <h1 style="margin:0 0 14px;font-size:24px;line-height:1.35;font-weight:600;color:#1f2328;">
+                Please verify your identity, {{ $name }}
+              </h1>
+              <p style="margin:0 0 22px;font-size:15px;line-height:1.6;color:#424a53;">
+                We received a request to reset the password for your Applyra account. Use the verification code below to continue.
+              </p>
+              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border:1px solid #d8dee4;border-radius:8px;">
+                <tr>
+                  <td style="padding:20px 22px 22px;">
+                    <p style="margin:0 0 12px;font-size:14px;line-height:1.5;color:#424a53;">
+                      Here is your Applyra password reset verification code:
+                    </p>
+                    <p style="margin:0 0 18px;text-align:center;font-family:'Courier New',Courier,monospace;font-size:32px;line-height:1.4;font-weight:700;letter-spacing:8px;color:#1f2328;">
+                      {{ $code }}
+                    </p>
+                    <p style="margin:0;font-size:14px;line-height:1.6;color:#424a53;">
+                      This code is valid for <strong>{{ $minutes }} minutes</strong> and can only be used once.
+                    </p>
+                  </td>
+                </tr>
+              </table>
+              <p style="margin:20px 0 10px;font-size:14px;line-height:1.6;color:#424a53;">
+                <strong>Please don't share this code with anyone.</strong> Applyra will never ask you to provide it by phone or email.
+              </p>
+              <p style="margin:0;font-size:14px;line-height:1.6;color:#57606a;">
+                If you didn't request this code, you can safely ignore this email. Your password will remain unchanged.
+              </p>
+              <p style="margin:22px 0 0;font-size:14px;line-height:1.6;color:#424a53;">
+                Thanks,<br>The Applyra Team
+              </p>
+            </td>
+          </tr>
+          <tr>
+            <td align="center" style="padding:18px 12px 0;font-size:12px;line-height:1.5;color:#6e7781;">
+              This message was sent because a password reset was requested for an Applyra account.
+            </td>
+          </tr>
+        </table>
+      </td>
+    </tr>
+  </table>
 </body>
 </html>
diff --git a/jobs-backend/tests/Feature/PasswordOtpMailTest.php b/jobs-backend/tests/Feature/PasswordOtpMailTest.php
new file mode 100644
index 0000000..3ee75fa
--- /dev/null
+++ b/jobs-backend/tests/Feature/PasswordOtpMailTest.php
@@ -0,0 +1,45 @@
+<?php
+
+namespace Tests\Feature;
+
+use App\Mail\PasswordOtpMail;
+use App\Models\User;
+use Illuminate\Foundation\Testing\RefreshDatabase;
+use Illuminate\Support\Facades\Mail;
+use Tests\TestCase;
+
+class PasswordOtpMailTest extends TestCase
+{
+    use RefreshDatabase;
+
+    public function test_forgot_password_sends_a_branded_single_use_code_email(): void
+    {
+        Mail::fake();
+        $user = User::factory()->create([
+            'name' => 'Sara Ali',
+            'email' => 'sara@example.com',
+        ]);
+
+        $this->postJson('/api/auth/forgot-password', ['email' => $user->email])
+            ->assertOk()
+            ->assertJsonPath('message', 'If that email has an account, a 6-digit code is on its way.');
+
+        Mail::assertSent(PasswordOtpMail::class, function (PasswordOtpMail $mail) use ($user): bool {
+            $html = $mail->render();
+            $text = view('emails.password-otp-text', [
+                'code' => $mail->code,
+                'minutes' => $mail->minutes,
+                'name' => $mail->name,
+            ])->render();
+
+            return $mail->hasTo($user->email)
+                && $mail->name === 'Sara Ali'
+                && $mail->minutes === 10
+                && preg_match('/^\d{6}$/', $mail->code) === 1
+                && str_contains($html, 'Please verify your identity, Sara Ali')
+                && str_contains($html, 'Here is your Applyra password reset verification code:')
+                && str_contains($html, 'This code is valid for')
+                && str_contains($text, $mail->code);
+        });
+    }
+}
OTP_EMAIL_PATCH

if ! git apply --check "$patch_file"; then
  echo "Could not apply cleanly. The project files may have changed; no patch was applied." >&2
  exit 1
fi
git apply "$patch_file"
echo "Applyra OTP email update applied. Review with: git status --short"
