<?php

use App\Http\Controllers\AuthController;
use App\Http\Controllers\ChatController;
use App\Http\Controllers\JobController;
use Illuminate\Support\Facades\Route;
use App\Http\Controllers\PasswordResetController;



Route::get('/stats', [JobController::class, 'stats']);
Route::get('/jobs', [JobController::class, 'index']);
Route::get('/suggest', [JobController::class, 'suggest']);
Route::post('/chat', [ChatController::class, 'message'])->middleware('throttle:600,1');
Route::post('/chat/stream', [ChatController::class, 'stream'])->middleware('throttle:600,1');

Route::prefix('auth')->group(function () {
    Route::post('/register', [AuthController::class, 'register'])->middleware('throttle:10,1');
    Route::post('/login', [AuthController::class, 'login'])->middleware('throttle:20,1');

    Route::middleware('auth:sanctum')->group(function () {
        Route::get('/me', [AuthController::class, 'me']);
        Route::post('/logout', [AuthController::class, 'logout']);
        Route::put('/password', [AuthController::class, 'updatePassword']);
    });
});

Route::prefix('auth')->middleware('throttle:5,1')->group(function () {
    Route::post('/forgot-password', [PasswordResetController::class, 'forgot']);
    Route::post('/reset-password', [PasswordResetController::class, 'reset']);
});

Route::post('/forgot-password', [\App\Http\Controllers\AuthController::class, 'forgotPassword'])->middleware('throttle:10,1');
Route::post('/reset-password', [\App\Http\Controllers\AuthController::class, 'resetPassword'])->middleware('throttle:10,1');
Route::post('/update-password', [\App\Http\Controllers\AuthController::class, 'updatePassword'])->middleware('auth:sanctum');

require __DIR__ . '/chat.php';

// --- profile: photo, personal details, CV and CV auto-fill ---------------------------------
Route::prefix('profile')->middleware('auth:sanctum')->group(function () {
    Route::get('/', [\App\Http\Controllers\ProfileController::class, 'show']);
    Route::put('/', [\App\Http\Controllers\ProfileController::class, 'update'])->middleware('throttle:30,1');
    Route::get('/national-number', [\App\Http\Controllers\ProfileController::class, 'nationalNumber'])->middleware('throttle:10,1');
    Route::get('/photo', [\App\Http\Controllers\ProfileController::class, 'photo']);
    Route::post('/photo', [\App\Http\Controllers\ProfileController::class, 'uploadPhoto'])->middleware('throttle:20,1');
    Route::delete('/photo', [\App\Http\Controllers\ProfileController::class, 'deletePhoto']);
    Route::get('/cv', [\App\Http\Controllers\ProfileController::class, 'downloadCv']);
    Route::post('/cv', [\App\Http\Controllers\ProfileController::class, 'uploadCv'])->middleware('throttle:10,1');
    Route::post('/cv/autofill', [\App\Http\Controllers\ProfileController::class, 'autofill'])->middleware('throttle:20,1');
    Route::delete('/cv', [\App\Http\Controllers\ProfileController::class, 'deleteCv']);
});
