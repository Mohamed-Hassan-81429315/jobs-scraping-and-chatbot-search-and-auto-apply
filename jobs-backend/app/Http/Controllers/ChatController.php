<?php

namespace App\Http\Controllers;

use App\Services\Chat\JobAssistant;
use App\Services\Chat\MistralException;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\RateLimiter;
use Symfony\Component\HttpFoundation\StreamedResponse;

class ChatController extends Controller
{
    /** One-shot JSON answer (kept as a fallback for clients that cannot stream). */
    public function message(Request $request): JsonResponse
    {
        $apiKey = $this->apiKey($request);
        if ($apiKey === null) {
            return $this->keyRequired();
        }

        $data = $this->validated($request);

        if ($limited = $this->limited($apiKey)) {
            return $limited;
        }

        try {
            return response()->json($this->assistant($apiKey, $data));
        } catch (MistralException $e) {
            return response()->json($this->errorBody($e), $this->errorStatus($e));
        } catch (\Throwable $e) {
            report($e);

            return response()->json($this->genericError(), 500);
        }
    }

    /**
     * Server-sent events:
     *   status {stage}   planning | searching | ranking | writing
     *   jobs   {jobs,total}
     *   token  {t}       pieces of the answer as Mistral writes it
     *   done   {...}     the complete final payload
     *   error  {code,reply}
     */
    public function stream(Request $request): StreamedResponse|JsonResponse
    {
        $apiKey = $this->apiKey($request);
        if ($apiKey === null) {
            return $this->keyRequired();
        }

        $data = $this->validated($request);

        if ($limited = $this->limited($apiKey)) {
            return $limited;
        }

        return response()->stream(function () use ($apiKey, $data) {
            @set_time_limit(120);
            while (ob_get_level() > 0) {
                @ob_end_flush();
            }

            $send = function (string $event, array $payload = []): void {
                echo 'event: ' . $event . "\n";
                echo 'data: ' . json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_INVALID_UTF8_SUBSTITUTE) . "\n\n";
                flush();
            };

            // Padding so proxies and PHP servers start flushing immediately.
            echo ':' . str_repeat(' ', 2048) . "\n\n";
            flush();

            try {
                $send('done', $this->assistant($apiKey, $data, $send));
            } catch (MistralException $e) {
                $send('error', $this->errorBody($e));
            } catch (\Throwable $e) {
                report($e);
                $send('error', $this->genericError());
            }
        }, 200, [
            'Content-Type'      => 'text/event-stream; charset=utf-8',
            'Cache-Control'     => 'no-cache, no-transform',
            'X-Accel-Buffering' => 'no',
        ]);
    }

    // ------------------------------------------------------------ helpers

    private function assistant(string $apiKey, array $data, ?callable $emit = null): array
    {
        return JobAssistant::make()->handle(
            $apiKey,
            trim($data['message']),
            $data['history'] ?? [],
            $data['last_search'] ?? null,
            $emit
        );
    }

    private function apiKey(Request $request): ?string
    {
        $apiKey = trim((string) $request->header('X-Mistral-Key', ''));

        if ($apiKey === '' || strlen($apiKey) > 300 || preg_match('/\s/', $apiKey)) {
            return null;
        }

        return $apiKey;
    }

    private function keyRequired(): JsonResponse
    {
        return response()->json([
            'code'  => 'key_required',
            'reply' => 'Please connect your Mistral API key to chat.',
        ], 401);
    }

    private function validated(Request $request): array
    {
        return $request->validate([
            'message'        => ['required', 'string', 'max:500'],
            'history'        => ['nullable', 'array', 'max:12'],
            'history.*.role' => ['required', 'string', 'in:user,bot'],
            'history.*.text' => ['required', 'string', 'max:1000'],
            'last_search'    => ['nullable', 'array'],
        ]);
    }

    /** Per API key (the Next.js server is the only direct caller, so per-IP would be shared). */
    private function limited(string $apiKey): ?JsonResponse
    {
        $limiterKey = 'chat:' . hash('sha256', $apiKey);

        if (RateLimiter::tooManyAttempts($limiterKey, (int) config('chat.rate_per_min', 20))) {
            return response()->json([
                'code'  => 'rate_limited',
                'reply' => 'You are sending messages too quickly. Please wait a few seconds.',
            ], 429);
        }

        RateLimiter::hit($limiterKey, 60);

        return null;
    }

    private function errorStatus(MistralException $e): int
    {
        return match ($e->reason) {
            'invalid_key'  => 401,
            'rate_limited' => 429,
            default        => 502,
        };
    }

    private function errorBody(MistralException $e): array
    {
        return match ($e->reason) {
            'invalid_key' => [
                'code'  => 'invalid_key',
                'reply' => 'Mistral rejected this API key. Please check it and connect again.',
            ],
            'rate_limited' => [
                'code'  => 'upstream_rate_limited',
                'reply' => 'Mistral is rate limiting this key right now. Please try again in a minute.',
            ],
            default => [
                'code'  => 'upstream',
                'reply' => 'The AI service is not responding right now. Please try again in a moment.',
            ],
        };
    }

    private function genericError(): array
    {
        return [
            'code'  => 'error',
            'reply' => 'Something went wrong on our side. Please try again.',
        ];
    }
}
