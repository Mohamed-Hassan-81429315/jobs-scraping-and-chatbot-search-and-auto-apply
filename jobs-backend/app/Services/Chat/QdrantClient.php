<?php

namespace App\Services\Chat;

use Illuminate\Http\Client\PendingRequest;
use Illuminate\Support\Facades\Http;

class QdrantClient
{
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

    /** @return array{points:int,dim:?int}|null  null when the collection does not exist */
    public function info(): ?array
    {
        $res = $this->http()->get($this->path());
        if (!$res->successful()) {
            return null;
        }

        $vectors = $res->json('result.config.params.vectors');
        $dim     = is_array($vectors) && isset($vectors['size']) ? (int) $vectors['size'] : null;

        return ['points' => (int) ($res->json('result.points_count') ?? 0), 'dim' => $dim];
    }

    /** Creates the collection, and refuses to reuse one built for a different vector size. */
    public function ensureCollection(int $dim, bool $fresh = false): void
    {
        if ($fresh && $this->info() !== null) {
            $this->http()->delete($this->path())->throw();
        }

        $info = $this->info();

        if ($info === null) {
            $this->http()->put($this->path(), [
                'vectors' => ['size' => $dim, 'distance' => 'Cosine'],
            ])->throw();

            return;
        }

        if ($info['dim'] !== null && $info['dim'] !== $dim) {
            throw new \RuntimeException(
                "Qdrant collection '{$this->collection}' stores {$info['dim']}-dimension vectors but the embedding "
                . "model produces {$dim}. Use a different QDRANT_COLLECTION or run: php artisan jobs:embed --fresh"
            );
        }
    }

    /** @param array<int,int> $ids  @return array<int,?string> job id => stored content hash */
    public function existingHashes(array $ids): array
    {
        $rows = $this->http()->post($this->path('/points'), [
            'ids'          => array_values($ids),
            'with_payload' => ['hash'],
            'with_vector'  => false,
        ])->throw()->json('result') ?? [];

        $out = [];
        foreach ($rows as $row) {
            $out[(int) $row['id']] = $row['payload']['hash'] ?? null;
        }

        return $out;
    }

    public function upsert(array $points): void
    {
        $this->http()->timeout(120)->put($this->path('/points?wait=true'), ['points' => $points])->throw();
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
            if ($this->info() === null) {
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
            $points = $this->http()->post($this->path('/points/search'), $legacy)->throw()->json('result') ?? [];
        } else {
            $points = $res->throw()->json('result.points') ?? [];
        }

        return array_map(
            fn ($p) => ['id' => (int) $p['id'], 'score' => (float) $p['score']],
            $points
        );
    }
}
