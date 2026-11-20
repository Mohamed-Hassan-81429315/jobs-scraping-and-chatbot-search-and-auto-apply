<?php

namespace App\Console\Commands;

use App\Models\Company;
use App\Models\Job;
use App\Models\Source;
use App\Models\Tag;
use Carbon\Carbon;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

class ImportJobs extends Command
{
    protected $signature = 'jobs:import {path : Full path to jobs.json}';
    protected $description = 'Import scraped jobs from jobs.json into the database';

    private array $sources = [];
    private array $companies = [];
    private array $tags = [];

    public function handle(): int
    {
        $path = $this->argument('path');
        if (!is_file($path)) {
            $this->error("File not found: $path");
            return self::FAILURE;
        }

        $data = json_decode(file_get_contents($path), true);
        $jobs = $data['jobs'] ?? $data;
        if (!is_array($jobs)) {
            $this->error('Invalid JSON structure.');
            return self::FAILURE;
        }

        $bar = $this->output->createProgressBar(count($jobs));
        $imported = 0;

        foreach (array_chunk($jobs, 500) as $chunk) {
            DB::transaction(function () use ($chunk, $bar, &$imported) {
                foreach ($chunk as $j) {
                    $bar->advance();
                    $title = trim((string) ($j['title'] ?? ''));
                    if ($title === '' || empty($j['id']) || empty($j['url'])) {
                        continue;
                    }

                    $posted = null;
                    if (!empty($j['posted_at'])) {
                        try {
                            $posted = Carbon::parse($j['posted_at'])->utc();
                        } catch (\Throwable $e) {
                        }
                    }

                    $job = Job::updateOrCreate(
                        ['external_id' => $j['id']],
                        [
                            'source_id'   => $this->source($j['source'] ?? 'unknown'),
                            'company_id'  => $this->company($j['company'] ?? ''),
                            'title'       => Str::limit($title, 500, ''),
                            'location'    => isset($j['location']) ? Str::limit((string) $j['location'], 500, '') : null,
                            'url'         => $j['url'],
                            'posted_at'   => $posted,
                            'description' => $j['description'] ?? null,
                        ]
                    );

                    $tagIds = [];
                    foreach ((array) ($j['tags'] ?? []) as $tag) {
                        if (is_string($tag) && trim($tag) !== '') {
                            $tagIds[] = $this->tag($tag);
                        }
                    }
                    $job->tags()->sync(array_unique($tagIds));
                    $imported++;
                }
            });
        }

        $bar->finish();
        $this->newLine(2);
        $this->info("Imported/updated $imported jobs.");
        return self::SUCCESS;
    }

    private function source(string $name): int
    {
        return $this->sources[$name] ??= Source::firstOrCreate(['name' => $name])->id;
    }

    private function company(string $name): int
    {
        $name = trim($name) === '' ? 'Unknown' : Str::limit(trim($name), 255, '');
        return $this->companies[$name] ??= Company::firstOrCreate(['name' => $name])->id;
    }

    private function tag(string $name): int
    {
        $name = Str::limit(trim($name), 190, '');
        return $this->tags[mb_strtolower($name)] ??= Tag::firstOrCreate(['name' => $name])->id;
    }
}