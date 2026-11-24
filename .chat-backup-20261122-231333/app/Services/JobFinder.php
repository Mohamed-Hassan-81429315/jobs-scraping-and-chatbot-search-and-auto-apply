<?php

namespace App\Services;

use App\Models\Job;
use Illuminate\Support\Collection;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Str;

/**
 * Searches the collected job listings. Used as the "search_jobs" tool for the AI model
 * and as the plain keyword search when the AI provider is unavailable.
 */
class JobFinder
{
    private const STOP = [
        'a', 'an', 'the', 'i', 'me', 'my', 'we', 'you', 'am', 'is', 'are', 'for', 'in', 'on', 'at', 'to', 'of', 'and', 'or',
        'with', 'want', 'need', 'looking', 'look', 'find', 'search', 'show', 'get', 'give', 'please', 'can', 'could', 'would',
        'job', 'jobs', 'work', 'position', 'positions', 'role', 'roles', 'vacancy', 'vacancies', 'opening', 'openings',
        'any', 'some', 'near', 'about', 'hiring', 'remote',
    ];

    /** @var array<string,bool> */
    private static array $columns = [];

    /** @return Collection<int,string> */
    public function keywords(string $text): Collection
    {
        return collect(preg_split('/[^\p{L}\p{N}\+\#\.]+/u', Str::lower($text), -1, PREG_SPLIT_NO_EMPTY))
            ->reject(fn ($w) => in_array($w, self::STOP, true) || Str::length($w) < 2)
            ->unique()->take(6)->values();
    }

    /**
     * @return Collection<int,array{id:mixed,title:string,company:?string,location:?string,url:?string}>
     */
    public function search(string $query, ?string $location = null, bool $remoteOnly = false, int $limit = 5): Collection
    {
        $limit = max(1, min($limit, 5));
        $words = $this->keywords($query);
        if ($words->isEmpty()) {
            return collect();
        }

        $table = (new Job)->getTable();
        $q = Job::query();
        if (method_exists(Job::class, 'company')) {
            $q->with('company');
        }

        $q->where(function ($w) use ($words) {
            foreach ($words as $kw) {
                $w->orWhere('title', 'like', '%'.$this->like($kw).'%');
            }
        });

        if ($location && $this->hasColumn($table, 'location')) {
            $q->where('location', 'like', '%'.$this->like($location).'%');
        }

        if ($remoteOnly) {
            $flag = collect(['is_remote', 'remote'])->first(fn ($c) => $this->hasColumn($table, $c));
            if ($flag) {
                $q->where($flag, true);
            } elseif ($this->hasColumn($table, 'location')) {
                $q->where('location', 'like', '%remote%');
            }
        }

        // Fetch a pool, then rank by how many keywords the title matches (newest first on ties).
        return $q->latest('id')->limit(40)->get()
            ->map(function (Job $job) use ($words) {
                $title = Str::lower((string) $job->getAttribute('title'));

                return ['score' => $words->filter(fn ($w) => str_contains($title, $w))->count(), 'job' => $job];
            })
            ->sort(fn ($a, $b) => [$b['score'], $b['job']->getKey()] <=> [$a['score'], $a['job']->getKey()])
            ->take($limit)
            ->map(fn ($row) => $this->present($row['job']))
            ->values();
    }

    private function present(Job $job): array
    {
        $attrs = $job->getAttributes();
        $url = collect(['apply_url', 'url', 'job_url', 'link'])
            ->map(fn ($k) => $attrs[$k] ?? null)
            ->first(fn ($v) => is_string($v) && Str::startsWith($v, ['http://', 'https://']));

        $company = null;
        try {
            $company = method_exists($job, 'company') ? $job->company?->name : null;
        } catch (\Throwable) {
        }

        return [
            'id' => $job->getKey(),
            'title' => (string) ($attrs['title'] ?? 'Untitled role'),
            'company' => $company ?? (isset($attrs['company']) && is_string($attrs['company']) ? $attrs['company'] : null),
            'location' => isset($attrs['location']) ? (string) $attrs['location'] : null,
            'url' => $url,
        ];
    }

    private function like(string $v): string
    {
        return addcslashes($v, '%_\\');
    }

    private function hasColumn(string $table, string $col): bool
    {
        return self::$columns["$table.$col"] ??= Schema::hasColumn($table, $col);
    }
}
