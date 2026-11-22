<?php

namespace App\Services\Chat;

use Illuminate\Http\Client\PendingRequest;
use Illuminate\Support\Facades\Http;

class QdrantClient
{
    /** Payload fields used in filters. Indexed so filtered search stays fast on big collections. */
    private const INDEXES = [
        'source'          => 'keyword',
        'remote'          => 'bool',
        'posted_ts'       => 'integer',
        'location_tokens' => 'keyword',
    ];

    public function __construct(
        private string $url,
        private string $collection,
        private string $apiKey = '',
    ) {
    }

    public static function fromConfig(): self
    {
        return new self(
            (string) config('chat.qdrant.url'),
            (string) config('chat.qdrant.collection'),
            (string) config('chat.qdrant.api_key'),
        );
    }

    private function http(): PendingRequest
    {
        $request = Http::baseUrl(rtrim($this->url, '/'))->acceptJson()->asJson()->timeout(30);

        return $this->apiKey !== '' ? $request->withHeaders(['api-key' => $this->apiKey]) : $request;
    }

    private function path(string $suffix = ''): string
    {
        return '/collections/' . rawurlencode($this->collection) . $suffix;
    }

    public function ensureCollection(int $dim, bool $fresh = false): void
    {
        $exists = $this->http()->get($this->path())->successful();

        if ($exists && $fresh) {
            $this->http()->delete($this->path())->throw();
            $exists = false;
        }

        if (!$exists) {
            $this->http()->put($this->path(), [
                'vectors' => ['size' => $dim, 'distance' => 'Cosine'],
            ])->throw();
        }

        $this->ensurePayloadIndexes();
    }

    /** Idempotent. Failures are ignored: filters still work without an index, only slower. */
    private function ensurePayloadIndexes(): void
    {
        foreach (self::INDEXES as $field => $schema) {
            try {
                $this->http()->put($this->path('/index?wait=true'), [
                    'field_name'   => $field,
                    'field_schema' => $schema,
                ]);
            } catch (\Throwable $e) {
                report($e);
            }
        }
    }

    /** @param array<int,int> $ids  @return array<int,array{hash:?string,pv:int}> */
    public function existingMeta(array $ids): array
    {
        $rows = $this->http()->post($this->path('/points'), [
            'ids'          => array_values($ids),
            'with_payload' => ['hash', 'pv'],
            'with_vector'  => false,
        ])->throw()->json('result') ?? [];

        $out = [];
        foreach ($rows as $row) {
            $out[(int) $row['id']] = [
                'hash' => $row['payload']['hash'] ?? null,
                'pv'   => (int) ($row['payload']['pv'] ?? 0),
            ];
        }

        return $out;
    }

    public function upsert(array $points): void
    {
        $this->http()->timeout(120)->put($this->path('/points?wait=true'), ['points' => $points])->throw();
    }

    /** Update the payload of existing points without touching their vectors. @param array<int,array> $byId */
    public function setPayloads(array $byId): void
    {
        $ops = [];
        foreach ($byId as $id => $payload) {
            $ops[] = ['set_payload' => ['payload' => $payload, 'points' => [(int) $id]]];
        }

        foreach (array_chunk($ops, 100) as $chunk) {
            $this->http()->timeout(60)->post($this->path('/points/batch?wait=true'), ['operations' => $chunk])->throw();
        }
    }

    /**
     * Cosine search. Only points with score >= $minScore come back.
     *
     * @return array<int,array{id:int,score:float}>
     */
    public function search(array $vector, float $minScore, int $limit, array $filter = []): array
    {
        $body = [
            'query'           => $vector,
            'limit'           => $limit,
            'score_threshold' => $minScore,
            'with_payload'    => false,
            'with_vector'     => false,
        ];
        if ($filter) {
            $body['filter'] = $filter;
        }

        $res = $this->http()->post($this->path('/points/query'), $body);

        if ($res->status() === 404) {
            if (!$this->http()->get($this->path())->successful()) {
                throw new \RuntimeException('Qdrant collection not found. Run: php artisan jobs:embed');
            }

            // Older Qdrant servers have no /points/query.
            $legacy = [
                'vector'          => $vector,
                'limit'           => $limit,
                'score_threshold' => $minScore,
                'with_payload'    => false,
                'with_vector'     => false,
            ];
            if ($filter) {
                $legacy['filter'] = $filter;
            }
            $res    = $this->http()->post($this->path('/points/search'), $legacy)->throw();
            $points = $res->json('result') ?? [];
        } else {
            $points = $res->throw()->json('result.points') ?? [];
        }

        return array_map(
            fn ($p) => ['id' => (int) $p['id'], 'score' => (float) $p['score']],
            $points
        );
    }
}
