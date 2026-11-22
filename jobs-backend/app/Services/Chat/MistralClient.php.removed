<?php

namespace App\Services\Chat;

use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\Client\PendingRequest;
use Illuminate\Http\Client\Response;
use Illuminate\Support\Facades\Http;

class MistralClient
{
    public function __construct(
        private string $baseUrl,
        private string $chatModel,
        private string $embedModel,
    ) {
    }

    public static function fromConfig(): self
    {
        return new self(
            (string) config('chat.mistral.base_url'),
            (string) config('chat.mistral.chat_model'),
            (string) config('chat.mistral.embed_model'),
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

    private function fail(int $status): never
    {
        if ($status === 401 || $status === 403) {
            throw new MistralException('Mistral rejected the API key.', 'invalid_key', 401);
        }
        if ($status === 429) {
            throw new MistralException('Mistral rate limit reached.', 'rate_limited', 429);
        }

        throw new MistralException('Mistral returned HTTP ' . $status . '.', 'upstream', 502);
    }

    /** POST with a small retry on 429 / 5xx. The API key never appears in errors. */
    private function post(string $key, string $path, array $body, int $attempts = 3): Response
    {
        $last = null;

        for ($i = 0; $i < $attempts; $i++) {
            try {
                $res = $this->http($key)->post($path, $body);
            } catch (ConnectionException) {
                if ($i === $attempts - 1) {
                    throw new MistralException('Could not reach Mistral.', 'network', 502);
                }
                sleep(1 << $i);
                continue;
            }

            $status = $res->status();

            if ($status === 401 || $status === 403) {
                throw new MistralException('Mistral rejected the API key.', 'invalid_key', 401);
            }

            if (($status === 429 || $status >= 500) && $i < $attempts - 1) {
                sleep(min(8, 1 << ($i + 1)));
                continue;
            }

            $last = $res;
            break;
        }

        if ($last === null) {
            throw new MistralException('No response from Mistral.', 'network', 502);
        }
        if ($last->status() === 429) {
            throw new MistralException('Mistral rate limit reached.', 'rate_limited', 429);
        }
        if ($last->failed()) {
            throw new MistralException('Mistral returned HTTP ' . $last->status() . '.', 'upstream', 502);
        }

        return $last;
    }

    /** Chat completion in JSON mode. The messages must mention the word JSON. */
    public function chatJson(string $key, array $messages, int $maxTokens = 500, float $temperature = 0.1): array
    {
        $res = $this->post($key, '/chat/completions', [
            'model'           => $this->chatModel,
            'messages'        => $messages,
            'temperature'     => $temperature,
            'max_tokens'      => $maxTokens,
            'response_format' => ['type' => 'json_object'],
        ]);

        $content = $res->json('choices.0.message.content');
        if (is_string($content)) {
            $content = trim((string) preg_replace('/^```(?:json)?\s*|\s*```$/', '', trim($content)));
        }

        $data = is_string($content) ? json_decode($content, true) : null;
        if (!is_array($data)) {
            throw new MistralException('The model did not return valid JSON.', 'bad_json', 502);
        }

        return $data;
    }

    /**
     * Plain-text chat completion. With $onToken the answer is streamed
     * (server-sent events from Mistral) and every piece is passed to the callback.
     * Always returns the full text.
     */
    public function chatText(
        string $key,
        array $messages,
        int $maxTokens = 300,
        float $temperature = 0.4,
        ?callable $onToken = null
    ): string {
        $body = [
            'model'       => $this->chatModel,
            'messages'    => $messages,
            'temperature' => $temperature,
            'max_tokens'  => $maxTokens,
        ];

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
            throw new MistralException('Could not reach Mistral.', 'network', 502);
        }

        if ($res->failed()) {
            $this->fail($res->status());
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
                if (is_array($delta)) {
                    $delta = implode('', array_map(fn ($part) => is_array($part) ? (string) ($part['text'] ?? '') : (string) $part, $delta));
                }
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
        $res = $this->post($key, '/embeddings', [
            'model' => $this->embedModel,
            'input' => array_values($texts),
        ]);

        $rows = $res->json('data') ?? [];
        usort($rows, fn ($a, $b) => ($a['index'] ?? 0) <=> ($b['index'] ?? 0));

        $vectors = array_map(
            fn ($row) => array_map('floatval', $row['embedding'] ?? []),
            $rows
        );

        if (count($vectors) !== count($texts) || in_array([], $vectors, true)) {
            throw new MistralException('Unexpected embeddings response.', 'upstream', 502);
        }

        return $vectors;
    }
}
