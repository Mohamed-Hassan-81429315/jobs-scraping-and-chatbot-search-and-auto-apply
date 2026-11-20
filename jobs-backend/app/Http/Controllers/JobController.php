<?php

namespace App\Http\Controllers;

use App\Models\Company;
use App\Models\Job;
use App\Models\Source;
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

    public function index(Request $request)
    {
        $request->validate([
            'q'      => 'nullable|string|max:100',
            'source' => 'nullable|string|max:100',
        ]);

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
            ->paginate(12)
            ->through(fn ($j) => [
                'id'        => $j->id,
                'title'     => $j->title,
                'company'   => $j->company->name,
                'source'    => $j->source->name,
                'location'  => $j->location,
                'url'       => $j->url,
                'posted_at' => $j->posted_at?->toIso8601String(),
                'excerpt'   => Str::limit(trim(preg_replace('/\s+/', ' ', strip_tags(html_entity_decode((string) $j->description)))), 220),
                'tags'      => $j->tags->pluck('name')->take(6)->values(),
            ]);
    }
}