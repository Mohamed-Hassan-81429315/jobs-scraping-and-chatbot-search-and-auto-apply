<?php

namespace App\Services\Chat;

use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\Client\PendingRequest;
use Illuminate\Http\Client\Response;
use Illuminate\Support\Facades\Http;

class OpenAIClient
{
    public function __construct(
        private string $baseUrl,
        private string $chatModel,
        private string $embedModel,
        private int $embedDim,
    ) {
    }

    public static function fromConfig(): self
    {
        return new self(
            (string) config('chat.openai.base_url'),
            (string) config('chat.openai.chat_model'),
            (string) config('chat.openai.embed_model'),
            (int) config('chat.openai.embed_dim'),
        );
    }

    private function http(string $key): PendingRequest
    {
        return Http::baseUrl(rtrim($this->baseUrl, '/'))
            ->withToken($key)
            ->acceptJson()
            ->asJson()
            ->timeout(60);
    }

    /** gpt-5*, o1, o3, o4...: no temperature, and hidden reasoning tokens count in the token budget. */
    private function isReasoningModel(): bool
    {
        return (bool) preg_match('/^(gpt-5|o\d)/', $this->chatModel);
    }

    /**
     * Chat completion that must return a JSON object matching $schema (Structured Outputs).
     * If the model rejects a parameter, the client repairs the request and retries.
     *
     * @param array{name:string,schema:array} $schema
     */
    public function chatJson(string $key, array $messages, array $schema, int $maxTokens = 500, float $temperature = 0.1): array
    {
        $reasoning = $this->isReasoningModel();

        $body = [
            'model'                 => $this->chatModel,
            'messages'              => $messages,
            'max_completion_tokens' => $reasoning ? max($maxTokens * 4, 1500) : $maxTokens,
            'response_format'       => [
                'type'        => 'json_schema',
                'json_schema' => ['name' => $schema['name'], 'strict' => true, 'schema' => $schema['schema']],
            ],
        ];

        if ($reasoning) {
            $body['reasoning_effort'] = 'low';
        } else {
            $body['temperature'] = $temperature;
        }

        $res    = $this->send($key, '/chat/completions', $body);
        $choice = $res->json('choices.0') ?? [];

        if (!empty($choice['message']['refusal'])) {
            throw new OpenAIException('The model declined this request.', 'refused', 422);
        }

        $content = $choice['message']['content'] ?? null;
        if (is_string($content)) {
            $content = trim((string) preg_replace('/^```(?:json)?\s*|\s*```$/', '', trim($content)));
        }

        $data = is_string($content) && $content !== '' ? json_decode($content, true) : null;
        if (!is_array($data)) {
            throw new OpenAIException('The model did not return valid JSON.', 'bad_json', 502);
        }

        return $data;
    }

    /** @param array<int,string> $texts  @return array<int,array<int,float>> */
    public function embed(string $key, array $texts): array
    {
        $body = [
            'model'           => $this->embedModel,
            'input'           => array_values($texts),
            'encoding_format' => 'float',
        ];
        if (str_starts_with($this->embedModel, 'text-embedding-3') && $this->embedDim > 0) {
            $body['dimensions'] = $this->embedDim;
        }

        $res  = $this->send($key, '/embeddings', $body);
        $rows = $res->json('data') ?? [];
        usort($rows, fn ($a, $b) => ($a['index'] ?? 0) <=> ($b['index'] ?? 0));

        $vectors = array_map(
            fn ($row) => array_map('floatval', $row['embedding'] ?? []),
            $rows
        );

        if (count($vectors) !== count($texts) || in_array([], $vectors, true)) {
            throw new OpenAIException('Unexpected embeddings response.', 'upstream', 502);
        }

        return $vectors;
    }

    /** POST with retries (429 / 5xx) and automatic repair of unsupported parameters. */
    private function send(string $key, string $path, array $body, int $attempts = 3): Response
    {
        $attempt = 0;
        $repairs = [];

        while (true) {
            try {
                $res = $this->http($key)->post($path, $body);
            } catch (ConnectionException) {
                if (++$attempt >= $attempts) {
                    throw new OpenAIException('Could not reach OpenAI.', 'network', 502);
                }
                sleep(1 << ($attempt - 1));
                continue;
            }

            if ($res->successful()) {
                return $res;
            }

            $status  = $res->status();
            $code    = (string) $res->json('error.code');
            $param   = (string) $res->json('error.param');
            $message = $this->shorten((string) $res->json('error.message'));

            if ($status === 401) {
                throw new OpenAIException('OpenAI rejected the API key.', 'invalid_key', 401);
            }
            if ($status === 403) {
                throw new OpenAIException($message !== '' ? $message : 'OpenAI denied access.', 'forbidden', 403);
            }
            if ($status === 404 || $code === 'model_not_found') {
                throw new OpenAIException('The configured OpenAI model is not available for this key.', 'model', 404);
            }
            if ($status === 429) {
                if ($code === 'insufficient_quota') {
                    throw new OpenAIException('The OpenAI account has no remaining quota.', 'quota', 402);
                }
                if (++$attempt >= $attempts) {
                    throw new OpenAIException('OpenAI rate limit reached.', 'rate_limited', 429);
                }
                $wait = (int) $res->header('Retry-After') ?: (1 << $attempt);
                sleep(min(10, max(1, $wait)));
                continue;
            }
            if ($status === 400 && $this->repair($body, $param, $repairs)) {
                continue;
            }
            if ($status >= 500) {
                if (++$attempt >= $attempts) {
                    throw new OpenAIException('OpenAI is not responding.', 'upstream', 502);
                }
                sleep(1 << ($attempt - 1));
                continue;
            }

            throw new OpenAIException('OpenAI rejected the request: ' . $message, 'upstream', 502);
        }
    }

    /** Drops or adapts a parameter the chosen model does not support. */
    private function repair(array &$body, string $param, array &$done): bool
    {
        if ($param === '' || isset($done[$param])) {
            return false;
        }

        switch ($param) {
            case 'temperature':
            case 'reasoning_effort':
            case 'dimensions':
                unset($body[$param]);
                break;
            case 'response_format':
                if (($body['response_format']['type'] ?? '') === 'json_schema') {
                    $body['response_format'] = ['type' => 'json_object'];
                } else {
                    unset($body['response_format']);
                }
                break;
            case 'max_completion_tokens':
                $body['max_tokens'] = $body['max_completion_tokens'];
                unset($body['max_completion_tokens']);
                break;
            case 'max_tokens':
                $body['max_completion_tokens'] = $body['max_tokens'];
                unset($body['max_tokens']);
                break;
            default:
                return false;
        }

        $done[$param] = true;

        return true;
    }

    private function shorten(string $text): string
    {
        return mb_substr(trim((string) preg_replace('/\s+/u', ' ', $text)), 0, 200);
    }
}
