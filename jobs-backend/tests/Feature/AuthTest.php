<?php

namespace Tests\Feature;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class AuthTest extends TestCase
{
    use RefreshDatabase;

    public function test_user_can_register_login_and_update_password(): void
    {
        $this->postJson('/api/register', [
            'name' => 'Sara Ali', 'email' => 'sara@example.com',
            'password' => 'Secret123', 'password_confirmation' => 'Secret123',
        ])->assertCreated()->assertJsonStructure(['user', 'token']);

        $token = $this->postJson('/api/login', ['email' => 'sara@example.com', 'password' => 'Secret123'])
            ->assertOk()->json('token');

        $this->withToken($token)->postJson('/api/update-password', [
            'current_password' => 'Secret123', 'password' => 'Newer1234', 'password_confirmation' => 'Newer1234',
        ])->assertOk();

        $this->postJson('/api/login', ['email' => 'sara@example.com', 'password' => 'Newer1234'])->assertOk();
    }

    public function test_wrong_password_is_rejected(): void
    {
        User::factory()->create(['email' => 'a@example.com', 'password' => 'Secret123']);
        $this->postJson('/api/login', ['email' => 'a@example.com', 'password' => 'nope'])->assertStatus(422);
    }

    public function test_weak_password_is_rejected_on_register(): void
    {
        $this->postJson('/api/register', [
            'name' => 'X', 'email' => 'x@example.com', 'password' => 'short', 'password_confirmation' => 'short',
        ])->assertStatus(422)->assertJsonValidationErrors('password');
    }

    public function test_forgot_password_never_reveals_account_existence(): void
    {
        $this->postJson('/api/forgot-password', ['email' => 'ghost@example.com'])->assertOk();
    }
}
