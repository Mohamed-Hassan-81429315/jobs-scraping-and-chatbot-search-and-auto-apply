<?php

namespace App\Console\Commands;

use App\Models\Job;
use App\Services\Chat\JobText;
use App\Services\Chat\OpenAIClient;
use App\Services\Chat\OpenAIException;
use App\Services\Chat\QdrantClient;
use Illuminate\Console\Command;

class EmbedJobs extends Command
{
    protected $signature = 'jobs:embed
        {--fresh : Rebuild the vector collection from scratch}
        {--limit=0 : Stop after embedding this many jobs (0 = no limit)}
        {--batch=64 : Jobs per embedding request}';

    protected $description = 'Embed jobs with OpenAI and store the vectors in Qdrant (only new or changed jobs)';

    public function handle(): int
    {
        $key = (string) config('chat.openai.operator_key');
        if ($key === '') {
            $this->error('Set OPENAI_API_KEY in jobs-backend/.env (an operator key used only for indexing).');

            return self::FAILURE;
        }

        $openai = OpenAIClient::fromConfig();
        $qdrant = QdrantClient::fromConfig();
        $dim    = (int) config('chat.openai.embed_dim');
        $model  = (string) config('chat.openai.embed_model');

        try {
            $qdrant->ensureCollection($dim, (bool) $this->option('fresh'));
        } catch (\Throwable $e) {
            $this->error($e->getMessage());

            return self::FAILURE;
        }

        $limit    = max(0, (int) $this->option('limit'));
        $batch    = max(1, min(128, (int) $this->option('batch')));
        $embedded = 0;
        $skipped  = 0;
        $stop     = false;
        $bar      = $this->output->createProgressBar(Job::count());

        try {
            Job::with(['company:id,name', 'source:id,name', 'tags:id,name'])
                ->chunkById(200, function ($jobs) use ($openai, $qdrant, $key, $dim, $model, $limit, $batch, &$embedded, &$skipped, &$stop, $bar) {
                    $byId   = $jobs->keyBy('id');
                    $texts  = [];
                    $hashes = [];

                    foreach ($jobs as $job) {
                        $texts[$job->id]  = JobText::forJob($job);
                        // The model name is part of the hash: switching models re-embeds everything.
                        $hashes[$job->id] = md5($model . "\n" . $texts[$job->id]);
                    }

                    $existing = $qdrant->existingHashes(array_keys($texts));
                    $todo     = array_values(array_filter(
                        array_keys($texts),
                        fn ($id) => ($existing[$id] ?? null) !== $hashes[$id]
                    ));
                    $skipped += count($texts) - count($todo);

                    foreach (array_chunk($todo, $batch) as $ids) {
                        if ($limit > 0 && $embedded >= $limit) {
                            $stop = true;
                            break;
                        }

                        $vectors = $openai->embed($key, array_map(fn ($id) => $texts[$id], $ids));
                        $points  = [];

                        foreach ($ids as $i => $id) {
                            if (count($vectors[$i]) !== $dim) {
                                throw new \RuntimeException(
                                    'Embedding size ' . count($vectors[$i]) . " does not match OPENAI_EMBED_DIM={$dim}."
                                );
                            }
                            $points[] = [
                                'id'      => $id,
                                'vector'  => $vectors[$i],
                                'payload' => JobText::payload($byId[$id], $hashes[$id]),
                            ];
                        }

                        $qdrant->upsert($points);
                        $embedded += count($ids);
                    }

                    $bar->advance($jobs->count());

                    return !$stop;
                });
        } catch (OpenAIException $e) {
            $this->newLine(2);
            $this->error('OpenAI error (' . $e->reason . '): ' . $e->getMessage());

            return self::FAILURE;
        } catch (\Throwable $e) {
            $this->newLine(2);
            $this->error($e->getMessage());

            return self::FAILURE;
        }

        $bar->finish();
        $this->newLine(2);
        $this->info("Embedded {$embedded} jobs, {$skipped} were already up to date.");

        return self::SUCCESS;
    }
}
