<?php

use App\Http\Controllers\JobController;
use Illuminate\Support\Facades\Route;

Route::get('/stats', [JobController::class, 'stats']);
Route::get('/jobs', [JobController::class, 'index']);
