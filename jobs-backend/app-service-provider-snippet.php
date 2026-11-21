<?php
// ADD inside AppServiceProvider::boot() in jobs-backend/app/Providers/AppServiceProvider.php
// use Illuminate\Auth\Notifications\ResetPassword;

ResetPassword::createUrlUsing(function ($notifiable, string $token) {
    $frontend = rtrim(config('app.frontend_url', env('FRONTEND_URL', 'http://localhost:3000')), '/');

    return $frontend.'/reset-password?token='.$token.'&email='.urlencode($notifiable->getEmailForPasswordReset());
});
