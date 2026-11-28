<?php

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
                'resetUrl' => 'http://x.test/reset-password?email=a#code=' . $mail->code,
            ])->render();

            return $mail->hasTo($user->email)
                && $mail->name === 'Sara Ali'
                && $mail->minutes === 10
                && preg_match('/^\d{6}$/', $mail->code) === 1
                && str_contains($html, 'Applyra logo')
                && preg_match('/src="cid:[^"]+"/', $html) === 1
                && str_contains($html, 'Please verify your identity, <strong>Sara Ali</strong>')
                && str_contains($html, 'Here is your Applyra password reset verification code:')
                && str_contains($html, 'This code is valid for')
                && str_contains($html, 'Copy OTP code')
                && str_contains($html, '/reset-password?email=sara%40example.com#code=' . $mail->code)
                                && str_contains($text, $mail->code);
        });
    }
}
