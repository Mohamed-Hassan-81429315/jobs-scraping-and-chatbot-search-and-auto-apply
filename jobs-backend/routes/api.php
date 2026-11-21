<?php

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
Route::post('/forgot-password', [\App\Http\Controllers\AuthController::class, 'forgotPassword'])->middleware('throttle:10,1');
Route::post('/reset-password', [\App\Http\Controllers\AuthController::class, 'resetPassword'])->middleware('throttle:10,1');
Route::post('/update-password', [\App\Http\Controllers\AuthController::class, 'updatePassword'])->middleware('auth:sanctum');
