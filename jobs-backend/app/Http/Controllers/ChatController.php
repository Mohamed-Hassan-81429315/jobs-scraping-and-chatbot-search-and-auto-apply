<?php

namespace App\Http\Controllers;

use App\Services\Chat\JobAssistant;
use App\Services\Chat\OpenAIException;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\RateLimiter;

class ChatController extends Controller
{
    public function message(Request $request): JsonResponse
    {
        $apiKey = trim((string) $request->header('X-OpenAI-Key', ''));

        if ($apiKey === '' || strlen($apiKey) > 300 || preg_match('/\s/', $apiKey)) {
            return response()->json([
                'code'  => 'key_required',
                'reply' => 'Please connect your OpenAI API key to chat.',
            ], 401);
        }

        $data = $request->validate([
            'message'        => ['required', 'string', 'max:500'],
            'history'        => ['nullable', 'array', 'max:12'],
            'history.*.role' => ['required', 'string', 'in:user,bot'],
            'history.*.text' => ['required', 'string', 'max:1000'],
            'last_search'    => ['nullable', 'array'],
        ]);

        // Per API key (the Next.js server is the only direct caller, so per-IP would be shared).
        $limiterKey = 'chat:' . hash('sha256', $apiKey);
        if (RateLimiter::tooManyAttempts($limiterKey, (int) config('chat.rate_per_min', 20))) {
            return response()->json([
                'code'  => 'rate_limited',
                'reply' => 'You are sending messages too quickly. Please wait a few seconds.',
            ], 429);
        }
        RateLimiter::hit($limiterKey, 60);

        try {
            $result = JobAssistant::make()->handle(
                $apiKey,
                trim($data['message']),
                $data['history'] ?? [],
                $data['last_search'] ?? null
            );

            return response()->json($result);
        } catch (OpenAIException $e) {
            [$code, $reply, $status] = match ($e->reason) {
                'invalid_key'  => ['invalid_key', 'OpenAI rejected this API key. Please check it and connect again.', 401],
                'quota'        => ['quota', 'This OpenAI account has no remaining credit or has reached its spending limit. Add credit in your OpenAI billing settings, then try again.', 402],
                'rate_limited' => ['upstream_rate_limited', 'OpenAI is rate limiting this key right now. Please try again in a minute.', 429],
                'model'        => ['model_unavailable', 'The AI model configured on this site is not available for your OpenAI key. The site owner can change OPENAI_CHAT_MODEL.', 503],
                'forbidden'    => ['forbidden', 'OpenAI denied access for this key (for example a restricted key or an unsupported region).', 403],
                default        => ['upstream', 'The AI service is not responding right now. Please try again in a moment.', 502],
            };

            return response()->json(['code' => $code, 'reply' => $reply], $status);
        } catch (\Throwable $e) {
            report($e);

            return response()->json([
                'code'  => 'error',
                'reply' => 'Something went wrong on our side. Please try again.',
            ], 500);
        }
    }
}
