<?php

namespace App\Services;

use Illuminate\Http\Client\PendingRequest;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Http;

class JobSearch
{
    public const PER_PAGE = 12;
    private const MAX_WINDOW = 10000;
    private const POSTED = ['24h' => 'now-1d', '7d' => 'now-7d', '30d' => 'now-30d'];

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
        $raw = fn (int $max) => ['type' => 'keyword', 'ignore_above' => $max];

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
                    'title'    => ['type' => 'text', 'fields' => ['ac' => $autocomplete, 'raw' => $raw(200)]],
                    'company'  => ['type' => 'text', 'fields' => ['ac' => $autocomplete, 'raw' => $raw(200)]],
                    'location' => ['type' => 'text', 'fields' => ['ac' => $autocomplete, 'raw' => $raw(150)]],
                    'tags'        => ['type' => 'text'],
                    'source'      => ['type' => 'keyword'],
                    'remote'      => ['type' => 'boolean'],
                    'description' => ['type' => 'text'],
                    'posted_at'   => ['type' => 'date'],
                ],
            ],
        ])->throw();
    }

    /** @param array<int, array> $docs map of job id => document */
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

    /** Filters shared by the result list and the facet counts. */
    private function filters(array $p, ?string $except = null): array
    {
        $f = [];

        if ($except !== 'source' && !empty($p['source'])) {
            $f[] = ['term' => ['source' => $p['source']]];
        }
        if ($except !== 'location' && !empty($p['location'])) {
            $f[] = ['term' => ['location.raw' => $p['location']]];
        }
        if ($except !== 'company' && !empty($p['company'])) {
            $f[] = ['term' => ['company.raw' => $p['company']]];
        }
        if ($except !== 'posted' && !empty($p['posted']) && isset(self::POSTED[$p['posted']])) {
            $f[] = ['range' => ['posted_at' => ['gte' => self::POSTED[$p['posted']]]]];
        }
        if ($except !== 'remote' && !empty($p['remote'])) {
            $f[] = ['term' => ['remote' => true]];
        }

        return $f;
    }

    public function search(array $p): array
    {
        $q       = trim((string) ($p['q'] ?? ''));
        $size    = self::PER_PAGE;
        $maxPage = intdiv(self::MAX_WINDOW, $size);
        $page    = max(1, min((int) ($p['page'] ?? 1), $maxPage));
        $from    = ($page - 1) * $size;

        $fields = ['title^4', 'company^3', 'tags^3', 'location^2', 'description'];
        $must   = [];
        $should = [];

        $terms = array_slice(preg_split('/\s+/u', $q, -1, PREG_SPLIT_NO_EMPTY) ?: [], 0, 8);
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
            $should[] = ['match_phrase' => ['title' => ['query' => $q, 'boost' => 5]]];
        } else {
            $must[] = ['match_all' => new \stdClass()];
        }

        $dateSort = ['posted_at' => ['order' => 'desc', 'missing' => '_last']];
        $sort = ($terms && ($p['sort'] ?? '') !== 'newest') ? ['_score', $dateSort] : [$dateSort];

        // Each facet ignores its own filter so people can switch between values.
        $facet = fn (string $own, array $agg) => [
            'filter' => ['bool' => ['filter' => $this->filters($p, $own)]],
            'aggs'   => ['f' => $agg],
        ];

        $res = $this->client()->post($this->name() . '/_search', [
            'from'             => $from,
            'size'             => $size,
            'track_total_hits' => true,
            '_source'          => ['title', 'company', 'source', 'location', 'url', 'posted_at', 'excerpt', 'tags', 'remote'],
            'query'            => ['bool' => ['must' => $must, 'should' => $should]],
            'post_filter'      => ['bool' => ['filter' => $this->filters($p)]],
            'sort'             => $sort,
            'aggs'             => [
                'sources'   => $facet('source', ['terms' => ['field' => 'source', 'size' => 10]]),
                'locations' => $facet('location', ['terms' => ['field' => 'location.raw', 'size' => 8]]),
                'companies' => $facet('company', ['terms' => ['field' => 'company.raw', 'size' => 8]]),
                'posted'    => $facet('posted', ['filters' => ['filters' => [
                    '24h' => ['range' => ['posted_at' => ['gte' => 'now-1d']]],
                    '7d'  => ['range' => ['posted_at' => ['gte' => 'now-7d']]],
                    '30d' => ['range' => ['posted_at' => ['gte' => 'now-30d']]],
                ]]]),
                'remote'    => $facet('remote', ['filter' => ['term' => ['remote' => true]]]),
            ],
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
                'remote'    => (bool) ($s['remote'] ?? false),
                'tags'      => array_slice($s['tags'] ?? [], 0, 6),
            ];
        }, $res['hits']['hits'] ?? []);

        $aggs    = $res['aggregations'] ?? [];
        $buckets = fn (string $n) => array_map(
            fn ($b) => ['key' => (string) $b['key'], 'count' => (int) $b['doc_count']],
            $aggs[$n]['f']['buckets'] ?? []
        );
        $posted = $aggs['posted']['f']['buckets'] ?? [];

        return [
            'data'         => $data,
            'total'        => $total,
            'per_page'     => $size,
            'current_page' => $page,
            'last_page'    => max(1, min((int) ceil($total / $size), $maxPage)),
            'facets'       => [
                'sources'   => $buckets('sources'),
                'locations' => $buckets('locations'),
                'companies' => $buckets('companies'),
                'posted'    => [
                    '24h' => (int) ($posted['24h']['doc_count'] ?? 0),
                    '7d'  => (int) ($posted['7d']['doc_count'] ?? 0),
                    '30d' => (int) ($posted['30d']['doc_count'] ?? 0),
                ],
                'remote'    => (int) ($aggs['remote']['f']['doc_count'] ?? 0),
            ],
        ];
    }

    public function suggest(string $q): array
    {
        $q = trim($q);

        if (mb_strlen($q) < 2) {
            return ['titles' => [], 'companies' => [], 'locations' => []];
        }

        return Cache::remember('suggest:' . md5(mb_strtolower($q)), 120, function () use ($q) {
            $match = fn (string $field) => ['match' => [$field => ['query' => $q, 'operator' => 'and']]];
            $agg   = fn (string $field, string $key, int $n) => [
                'filter' => $match($field),
                'aggs'   => ['k' => ['terms' => ['field' => $key, 'size' => $n]]],
            ];

            $res = $this->client(5)->post($this->name() . '/_search', [
                'size' => 0,
                'aggs' => [
                    't' => $agg('title.ac', 'title.raw', 6),
                    'c' => $agg('company.ac', 'company.raw', 4),
                    'l' => $agg('location.ac', 'location.raw', 4),
                ],
            ])->throw()->json();

            $keys = fn (string $n) => array_values(array_unique(array_map(
                fn ($b) => (string) $b['key'],
                $res['aggregations'][$n]['k']['buckets'] ?? []
            )));

            return ['titles' => $keys('t'), 'companies' => $keys('c'), 'locations' => $keys('l')];
        });
    }
}
