<?php

use App\Http\Controllers\ChatController;
use Illuminate\Support\Facades\Route;

// Loaded from routes/api.php, so these are /api/chat/...
Route::middleware(['auth:sanctum', 'throttle:120,1'])->prefix('chat')->group(function () {
    Route::get('/conversations', [ChatController::class, 'index']);
    Route::post('/conversations', [ChatController::class, 'store']);
    Route::get('/conversations/{id}', [ChatController::class, 'show'])->whereNumber('id');
    Route::post('/conversations/{id}/messages', [ChatController::class, 'append'])->whereNumber('id');
    Route::patch('/conversations/{id}', [ChatController::class, 'update'])->whereNumber('id');
    Route::delete('/conversations/{id}', [ChatController::class, 'destroy'])->whereNumber('id');
});
