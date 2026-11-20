<?php

namespace App\Http\Controllers;

use App\Models\Company;
use App\Models\Job;
use App\Models\Source;
use App\Services\JobSearch;
use Illuminate\Http\Request;
use Illuminate\Support\Str;

class JobController extends Controller
{
    public function stats()
    {
        return [
            'total_jobs'      => Job::count(),
            'total_companies' => Company::count(),
            'by_source'       => Source::withCount('jobs')->get()
                ->map(fn ($s) => ['name' => $s->name, 'count' => $s->jobs_count])
                ->sortByDesc('count')->values(),
        ];
    }

    public function index(Request $request, JobSearch $search)
    {
        $params = $request->validate([
            'q'        => 'nullable|string|max:100',
            'source'   => 'nullable|string|max:100',
            'location' => 'nullable|string|max:150',
            'company'  => 'nullable|string|max:255',
            'posted'   => 'nullable|in:24h,7d,30d',
            'remote'   => 'nullable|boolean',
            'sort'     => 'nullable|in:relevance,newest',
            'page'     => 'nullable|integer|min:1',
        ]);

        try {
            return $search->search($params);
        } catch (\Throwable $e) {
            // Elasticsearch is down or not indexed yet: use the basic MySQL search.
            report($e);
            return $this->mysqlSearch($request);
        }
    }

    public function suggest(Request $request, JobSearch $search)
    {
        $data = $request->validate(['q' => 'nullable|string|max:60']);

        try {
            return $search->suggest($data['q'] ?? '');
        } catch (\Throwable $e) {
            report($e);
            return ['titles' => [], 'companies' => [], 'locations' => []];
        }
    }

    private function mysqlSearch(Request $request)
    {
        $query = Job::with(['company:id,name', 'source:id,name', 'tags:id,name'])
            ->select(['id', 'title', 'location', 'url', 'posted_at', 'source_id', 'company_id', 'description']);

        if ($q = trim((string) $request->query('q'))) {
            foreach (preg_split('/\s+/', $q) as $word) {
                $like = '%' . addcslashes($word, '%_\\') . '%';
                $query->where(function ($w) use ($like) {
                    $w->where('title', 'like', $like)
                      ->orWhere('location', 'like', $like)
                      ->orWhereHas('company', fn ($c) => $c->where('name', 'like', $like))
                      ->orWhereHas('tags', fn ($t) => $t->where('name', 'like', $like));
                });
            }
        }

        if ($source = $request->query('source')) {
            $query->whereHas('source', fn ($s) => $s->where('name', $source));
        }

        return $query
            ->orderByRaw('posted_at IS NULL')
            ->orderByDesc('posted_at')
            ->paginate(JobSearch::PER_PAGE)
            ->through(fn ($j) => [
                'id'        => $j->id,
                'title'     => $j->title,
                'company'   => $j->company->name,
                'source'    => $j->source->name,
                'location'  => $j->location,
                'url'       => $j->url,
                'posted_at' => $j->posted_at?->toIso8601String(),
                'excerpt'   => Str::limit(trim(preg_replace('/\s+/', ' ', strip_tags(html_entity_decode((string) $j->description)))), 220),
                'remote'    => false,
                'tags'      => $j->tags->pluck('name')->take(6)->values(),
            ]);
    }
}
