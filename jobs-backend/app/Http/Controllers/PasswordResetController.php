<?php

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
