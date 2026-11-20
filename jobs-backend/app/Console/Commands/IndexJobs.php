<?php

namespace App\Console\Commands;

use App\Models\Job;
use App\Services\JobSearch;
use Illuminate\Console\Command;
use Illuminate\Support\Str;

class IndexJobs extends Command
{
    protected $signature = 'jobs:index {--fresh : Delete and rebuild the index from scratch}';
    protected $description = 'Index all jobs from MySQL into Elasticsearch';

    public function handle(JobSearch $search): int
    {
        try {
            $search->createIndex((bool) $this->option('fresh'));
        } catch (\Throwable $e) {
            $this->error('Cannot reach Elasticsearch at ' . config('elasticsearch.url') . ': ' . $e->getMessage());
            return self::FAILURE;
        }

        $bar = $this->output->createProgressBar(Job::count());

        Job::with(['company:id,name', 'source:id,name', 'tags:id,name'])
            ->chunkById(300, function ($jobs) use ($search, $bar) {
                $docs = [];

                foreach ($jobs as $job) {
                    $plain = trim(preg_replace(
                        '/\s+/u',
                        ' ',
                        strip_tags(html_entity_decode((string) $job->description))
                    ) ?? '');

                    $docs[$job->id] = [
                        'title'       => $job->title,
                        'company'     => $job->company->name,
                        'source'      => $job->source->name,
                        'location'    => $job->location,
                        'url'         => $job->url,
                        'posted_at'   => $job->posted_at?->toIso8601String(),
                        'description' => mb_substr($plain, 0, 20000),
                        'excerpt'     => Str::limit($plain, 220),
                        'tags'        => $job->tags->pluck('name')->values()->all(),
                    ];

                    $bar->advance();
                }

                $search->bulk($docs);
            });

        $search->refresh();
        $bar->finish();
        $this->newLine(2);
        $this->info('Elasticsearch index is up to date.');

        return self::SUCCESS;
    }
}
