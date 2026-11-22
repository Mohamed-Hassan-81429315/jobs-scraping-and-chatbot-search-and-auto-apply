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
        private int $embedDim = 0,
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
            ->timeout(45);
    }

    /** o-series and gpt-5 models are "reasoning" models: no custom temperature, reasoning tokens count. */
    private function isReasoningModel(): bool
    {
        return (bool) preg_match('/^(o\d|gpt-5)/i', $this->chatModel);
    }

    private function chatBody(array $messages, int $maxTokens, float $temperature): array
    {
        $body = [
            'model'                 => $this->chatModel,
            'messages'              => $messages,
            'max_completion_tokens' => $this->isReasoningModel() ? max($maxTokens * 4, 2000) : $maxTokens,
        ];

        if (!$this->isReasoningModel()) {
            $body['temperature'] = $temperature;
        }

        return $body;
    }

    /** Maps an HTTP error to an exception. The API key and OpenAI's error text never leave this class. */
    private function fail(Response $res): never
    {
        $status = $res->status();
        $code   = (string) ($res->json('error.code') ?? '');
        $type   = (string) ($res->json('error.type') ?? '');

        if ($status === 401) {
            throw new OpenAIException('OpenAI rejected the API key.', 'invalid_key', 401);
        }
        if ($status === 403) {
            throw new OpenAIException('OpenAI denied access for this key.', 'forbidden', 403);
        }
        if ($status === 429) {
            if ($code === 'insufficient_quota' || $type === 'insufficient_quota') {
                throw new OpenAIException('The OpenAI key has no quota left.', 'quota', 402);
            }

            throw new OpenAIException('OpenAI rate limit reached.', 'rate_limited', 429);
        }
        if ($status === 404 || $code === 'model_not_found') {
            throw new OpenAIException('The OpenAI model is not available for this key.', 'model', 502);
        }

        throw new OpenAIException('OpenAI returned HTTP ' . $status . '.', 'upstream', 502);
    }

    private function isQuota(Response $res): bool
    {
        return $res->status() === 429
            && (($res->json('error.code') ?? '') === 'insufficient_quota' || ($res->json('error.type') ?? '') === 'insufficient_quota');
    }

    /** POST with a small retry on rate limits (not quota) and 5xx. */
    private function post(string $key, string $path, array $body, int $attempts = 3): Response
    {
        for ($i = 0; $i < $attempts; $i++) {
            $last = $i === $attempts - 1;

            try {
                $res = $this->http($key)->post($path, $body);
            } catch (ConnectionException) {
                if ($last) {
                    throw new OpenAIException('Could not reach OpenAI.', 'network', 502);
                }
                sleep(1 << $i);
                continue;
            }

            $status = $res->status();

            if (!$last && (($status === 429 && !$this->isQuota($res)) || $status >= 500)) {
                $wait = (int) $res->header('Retry-After');
                sleep($wait > 0 ? min(8, $wait) : min(8, 1 << ($i + 1)));
                continue;
            }

            if ($res->failed()) {
                $this->fail($res);
            }

            return $res;
        }

        throw new OpenAIException('No response from OpenAI.', 'network', 502);
    }

    /** Chat completion in JSON mode. The messages must contain the word JSON. */
    public function chatJson(string $key, array $messages, int $maxTokens = 500, float $temperature = 0.1): array
    {
        $body = $this->chatBody($messages, $maxTokens, $temperature);
        $body['response_format'] = ['type' => 'json_object'];

        $res     = $this->post($key, '/chat/completions', $body);
        $content = $res->json('choices.0.message.content');

        if (is_string($content)) {
            $content = trim((string) preg_replace('/^```(?:json)?\s*|\s*```$/', '', trim($content)));
        }

        $data = is_string($content) && $content !== '' ? json_decode($content, true) : null;
        if (!is_array($data)) {
            throw new OpenAIException('The model did not return valid JSON.', 'bad_json', 502);
        }

        return $data;
    }

    /**
     * Plain-text chat completion. With $onToken the answer is streamed
     * (server-sent events) and every piece is passed to the callback.
     * Always returns the full text.
     */
    public function chatText(
        string $key,
        array $messages,
        int $maxTokens = 300,
        float $temperature = 0.4,
        ?callable $onToken = null
    ): string {
        $body = $this->chatBody($messages, $maxTokens, $temperature);

        if ($onToken === null) {
            $res = $this->post($key, '/chat/completions', $body);

            return trim((string) $res->json('choices.0.message.content'));
        }

        $body['stream'] = true;

        try {
            $res = $this->http($key)
                ->withOptions(['stream' => true])
                ->timeout(60)
                ->post('/chat/completions', $body);
        } catch (ConnectionException) {
            throw new OpenAIException('Could not reach OpenAI.', 'network', 502);
        }

        if ($res->failed()) {
            $this->fail($res);
        }

        $stream = $res->toPsrResponse()->getBody();
        $buffer = '';
        $full   = '';
        $done   = false;

        while (!$done && !$stream->eof()) {
            $chunk = $stream->read(1024);
            if ($chunk === '') {
                usleep(10000);
                continue;
            }
            $buffer .= $chunk;

            while (($pos = strpos($buffer, "\n")) !== false) {
                $line   = trim(substr($buffer, 0, $pos));
                $buffer = substr($buffer, $pos + 1);

                if (!str_starts_with($line, 'data:')) {
                    continue;
                }
                $payload = trim(substr($line, 5));
                if ($payload === '[DONE]') {
                    $done = true;
                    break;
                }

                $json  = json_decode($payload, true);
                $delta = $json['choices'][0]['delta']['content'] ?? '';
                if (is_string($delta) && $delta !== '') {
                    $full .= $delta;
                    $onToken($delta);
                }
            }
        }

        return trim($full);
    }

    /** @param array<int,string> $texts  @return array<int,array<int,float>> */
    public function embed(string $key, array $texts): array
    {
        // OpenAI rejects empty strings and inputs above 8191 tokens.
        $input = array_map(
            fn ($text) => trim((string) $text) === '' ? 'empty' : mb_substr((string) $text, 0, 8000),
            array_values($texts)
        );

        $body = ['model' => $this->embedModel, 'input' => $input];

        // Only the text-embedding-3 family accepts "dimensions".
        if ($this->embedDim > 0 && str_starts_with($this->embedModel, 'text-embedding-3')) {
            $body['dimensions'] = $this->embedDim;
        }

        $res  = $this->post($key, '/embeddings', $body);
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
}
