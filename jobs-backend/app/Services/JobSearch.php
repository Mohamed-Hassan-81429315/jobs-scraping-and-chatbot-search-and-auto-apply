<?php

namespace App\Services;

use Illuminate\Http\Client\PendingRequest;
use Illuminate\Support\Facades\Http;

class JobSearch
{
    public const PER_PAGE = 12;
    private const MAX_WINDOW = 10000; // Elasticsearch default result window

    private function client(int $timeout = 15): PendingRequest
    {
        return Http::baseUrl(rtrim(config('elasticsearch.url'), '/'))
            ->timeout($timeout)
            ->acceptJson();
    }

    private function name(): string
    {
        return config('elasticsearch.index');
    }

    public function createIndex(bool $fresh = false): void
    {
        $exists = $this->client()->head($this->name())->status() === 200;

        if ($exists && $fresh) {
            $this->client()->delete($this->name())->throw();
            $exists = false;
        }

        if ($exists) {
            return;
        }

        $autocomplete = [
            'type'            => 'text',
            'analyzer'        => 'autocomplete',
            'search_analyzer' => 'standard',
        ];

        $this->client()->put($this->name(), [
            'settings' => [
                'number_of_shards'   => 1,
                'number_of_replicas' => 0,
                'analysis' => [
                    'filter' => [
                        'edge_filter' => ['type' => 'edge_ngram', 'min_gram' => 2, 'max_gram' => 15],
                    ],
                    'analyzer' => [
                        'autocomplete' => [
                            'type'      => 'custom',
                            'tokenizer' => 'standard',
                            'filter'    => ['lowercase', 'edge_filter'],
                        ],
                    ],
                ],
            ],
            'mappings' => [
                'dynamic'    => false,
                'properties' => [
                    'title'       => ['type' => 'text', 'fields' => ['ac' => $autocomplete]],
                    'company'     => ['type' => 'text', 'fields' => ['ac' => $autocomplete]],
                    'location'    => ['type' => 'text'],
                    'tags'        => ['type' => 'text'],
                    'source'      => ['type' => 'keyword'],
                    'description' => ['type' => 'text'],
                    'posted_at'   => ['type' => 'date'],
                ],
            ],
        ])->throw();
    }

    /** @param array<int, array> $docs  map of job id => document */
    public function bulk(array $docs): void
    {
        $lines = '';
        $flags = JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE;

        foreach ($docs as $id => $doc) {
            $lines .= json_encode(['index' => ['_index' => $this->name(), '_id' => (string) $id]], $flags) . "\n";
            $lines .= json_encode($doc, $flags) . "\n";
        }

        $response = $this->client(120)
            ->withBody($lines, 'application/x-ndjson')
            ->post('_bulk')
            ->throw()
            ->json();

        if (!empty($response['errors'])) {
            foreach ($response['items'] as $item) {
                if (!empty($item['index']['error'])) {
                    throw new \RuntimeException('Bulk error: ' . json_encode($item['index']['error']));
                }
            }
        }
    }

    public function refresh(): void
    {
        $this->client()->send('POST', $this->name() . '/_refresh')->throw();
    }

    public function search(string $q, string $source, int $page): array
    {
        $size    = self::PER_PAGE;
        $maxPage = intdiv(self::MAX_WINDOW, $size);
        $page    = max(1, min($page, $maxPage));
        $from    = ($page - 1) * $size;

        $fields = ['title^4', 'company^3', 'tags^3', 'location^2', 'description'];
        $must   = [];
        $should = [];
        $filter = [];

        // Every word must match somewhere (typos and prefixes allowed).
        $terms = array_slice(preg_split('/\s+/u', trim($q), -1, PREG_SPLIT_NO_EMPTY) ?: [], 0, 8);
        foreach ($terms as $term) {
            $must[] = ['bool' => [
                'should' => [
                    ['multi_match' => [
                        'query'         => $term,
                        'fields'        => $fields,
                        'fuzziness'     => 'AUTO',
                        'prefix_length' => 1,
                    ]],
                    ['multi_match' => [
                        'query'  => $term,
                        'fields' => ['title.ac^2', 'company.ac'],
                    ]],
                ],
                'minimum_should_match' => 1,
            ]];
        }

        if ($terms) {
            // Rank exact phrases in the title first.
            $should[] = ['match_phrase' => ['title' => ['query' => $q, 'boost' => 5]]];
        } else {
            $must[] = ['match_all' => new \stdClass()];
        }

        if ($source !== '') {
            $filter[] = ['term' => ['source' => $source]];
        }

        $dateSort = ['posted_at' => ['order' => 'desc', 'missing' => '_last']];

        $res = $this->client()->post($this->name() . '/_search', [
            'from'             => $from,
            'size'             => $size,
            'track_total_hits' => true,
            '_source'          => ['title', 'company', 'source', 'location', 'url', 'posted_at', 'excerpt', 'tags'],
            'query'            => ['bool' => ['must' => $must, 'should' => $should, 'filter' => $filter]],
            'sort'             => $terms ? ['_score', $dateSort] : [$dateSort],
        ])->throw()->json();

        $total = (int) ($res['hits']['total']['value'] ?? 0);

        $data = array_map(function ($hit) {
            $s = $hit['_source'];

            return [
                'id'        => (int) $hit['_id'],
                'title'     => $s['title'] ?? '',
                'company'   => $s['company'] ?? '',
                'source'    => $s['source'] ?? '',
                'location'  => $s['location'] ?? null,
                'url'       => $s['url'] ?? '#',
                'posted_at' => $s['posted_at'] ?? null,
                'excerpt'   => $s['excerpt'] ?? '',
                'tags'      => array_slice($s['tags'] ?? [], 0, 6),
            ];
        }, $res['hits']['hits'] ?? []);

        return [
            'data'         => $data,
            'total'        => $total,
            'per_page'     => $size,
            'current_page' => $page,
            'last_page'    => max(1, min((int) ceil($total / $size), $maxPage)),
        ];
    }
}
