<?php

namespace App\Http\Controllers;

use App\Services\JobFinder;
use App\Services\OpenAIChat;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;
use Throwable;

class ChatController extends Controller
{
    public function __construct(private OpenAIChat $ai, private JobFinder $finder)
    {
    }

    public function message(Request $request): JsonResponse
    {
        $data = $request->validate([
            'message' => ['required', 'string', 'max:500'],
            'history' => ['sometimes', 'array', 'max:12'],
            'history.*.role' => ['required', 'in:user,assistant'],   // never "system" or "tool" from a browser
            'history.*.content' => ['required', 'string', 'max:1000'],
            'user_name' => ['sometimes', 'nullable', 'string', 'max:60'],
        ]);

        $message = trim($data['message']);
        $history = collect($data['history'] ?? [])
            ->map(fn ($t) => ['role' => $t['role'], 'content' => trim($t['content'])])
            ->filter(fn ($t) => $t['content'] !== '')
            ->take(-8)->values()->all();
        $name = trim((string) preg_replace('/[^\p{L}\p{N} \'\-]/u', '', (string) ($data['user_name'] ?? ''))) ?: null;

        if ($this->ai->enabled()) {
            try {
                return response()->json($this->ai->reply($message, $history, $name) + ['provider' => 'openai']);
            } catch (Throwable $e) {
                // Timeouts, 401/429/5xx, empty answers... never leave the user without a reply.
                Log::warning('OpenAI chat failed, using keyword fallback: '.$e->getMessage());
            }
        }

        return $this->keywordFallback($message);
    }

    /** Plain keyword search: used when OpenAI is not configured or temporarily failing. */
    private function keywordFallback(string $text): JsonResponse
    {
        $lower = Str::lower($text);

        if (preg_match('/^(hi|hello|hey|good (morning|afternoon|evening|night))\b/', $lower)) {
            return $this->say('Hello! Tell me a job title or skill, like "laravel developer", and I will search the listings.');
        }
        if (preg_match('/\b(help|what can you do|how does this work)\b/', $lower)) {
            return $this->say('I search the collected job listings. Type a job title, skill or field and I will show the latest matches with links to apply.');
        }

        try {
            $jobs = $this->finder->search($text);
        } catch (Throwable $e) {
            Log::warning('Keyword job search failed: '.$e->getMessage());

            return $this->say('The job search is temporarily unavailable. Please try again soon.');
        }

        if ($jobs->isEmpty()) {
            return $this->say('I found no listings for that. Try a broader title, like "developer" or "designer".');
        }

        return response()->json([
            'reply' => 'Here are the latest matches:',
            'jobs' => $jobs->all(),
            'provider' => 'fallback',
        ]);
    }

    private function say(string $reply): JsonResponse
    {
        return response()->json(['reply' => $reply, 'jobs' => [], 'provider' => 'fallback']);
    }
}
