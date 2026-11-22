<?php

namespace App\Console\Commands;

use App\Models\Job;
use App\Services\Chat\JobAssistant;
use App\Services\Chat\OpenAIClient;
use App\Services\Chat\OpenAIException;
use App\Services\Chat\QdrantClient;
use Illuminate\Console\Command;

class ChatDoctor extends Command
{
    protected $signature = 'chat:doctor {query? : A sample request used to inspect similarity scores}';

    protected $description = 'Check MySQL, Qdrant and OpenAI, and show real similarity scores to calibrate CHAT_MIN_SCORE';

    public function handle(): int
    {
        // MySQL
        try {
            $this->line('MySQL        OK    ' . number_format(Job::count()) . ' jobs');
        } catch (\Throwable $e) {
            $this->error('MySQL        FAIL  ' . $e->getMessage());

            return self::FAILURE;
        }

        // Qdrant
        $qdrant = QdrantClient::fromConfig();
        $dim    = (int) config('chat.openai.embed_dim');
        try {
            $info = $qdrant->info();
        } catch (\Throwable) {
            $this->error('Qdrant       FAIL  cannot reach ' . config('chat.qdrant.url') . ' (is the container running?)');

            return self::FAILURE;
        }

        $collection = (string) config('chat.qdrant.collection');
        if ($info === null) {
            $this->warn("Qdrant       WARN  collection '{$collection}' does not exist yet. Run: php artisan jobs:embed");
        } else {
            $this->line("Qdrant       OK    '{$collection}' holds " . number_format($info['points']) . ' vectors (' . ($info['dim'] ?? '?') . ' dimensions)');
            if ($info['dim'] !== null && $info['dim'] !== $dim) {
                $this->error("Qdrant       FAIL  dimension {$info['dim']} does not match OPENAI_EMBED_DIM={$dim}. Run: php artisan jobs:embed --fresh");

                return self::FAILURE;
            }
        }

        // OpenAI
        $key = (string) config('chat.openai.operator_key');
        if ($key === '') {
            $this->error('OpenAI       FAIL  set OPENAI_API_KEY (operator key) in jobs-backend/.env');

            return self::FAILURE;
        }

        $openai = OpenAIClient::fromConfig();

        try {
            $vector = $openai->embed($key, ['ping']);
            $this->line('Embeddings   OK    ' . config('chat.openai.embed_model') . ' -> ' . count($vector[0]) . ' dimensions');
        } catch (OpenAIException $e) {
            $this->error('Embeddings   FAIL  (' . $e->reason . ') ' . $e->getMessage());

            return self::FAILURE;
        }

        try {
            $schema = [
                'name'   => 'ping',
                'schema' => [
                    'type'                 => 'object',
                    'additionalProperties' => false,
                    'required'             => ['ok'],
                    'properties'           => ['ok' => ['type' => 'boolean']],
                ],
            ];
            $reply = $openai->chatJson($key, [
                ['role' => 'system', 'content' => 'Reply with a JSON object: {"ok": true}'],
                ['role' => 'user', 'content' => 'ping'],
            ], $schema, 50, 0.0);
            $this->line('Chat         OK    ' . config('chat.openai.chat_model') . ' -> ' . json_encode($reply));
        } catch (OpenAIException $e) {
            $this->error('Chat         FAIL  (' . $e->reason . ') ' . $e->getMessage());

            return self::FAILURE;
        }

        if ($info === null || $info['points'] === 0) {
            $this->warn('Nothing to probe yet. Run: php artisan jobs:embed');

            return self::SUCCESS;
        }

        // Probe: real scores for a real request
        $query = (string) ($this->argument('query') ?: 'remote python developer');

        try {
            $result = JobAssistant::make()->probe($key, $query, 15);
        } catch (OpenAIException $e) {
            $this->error('Probe        FAIL  (' . $e->reason . ') ' . $e->getMessage());

            return self::FAILURE;
        }

        $this->newLine();
        $this->line('Request: ' . $query);
        $this->line('Intent : ' . $result['plan']['intent']);

        if ($result['plan']['intent'] !== 'search') {
            $this->line('Reply  : ' . $result['plan']['reply']);

            return self::SUCCESS;
        }

        $this->line('Plan   : ' . json_encode($result['plan']['search'], JSON_UNESCAPED_UNICODE));
        $this->newLine();
        $this->line("Text that was embedded:\n" . $result['query_text']);
        $this->newLine();
        $this->table(['Raw cosine', 'Shown as', 'Title', 'Company'], $result['rows']);

        $min = (float) config('chat.min_score');
        $this->info("Current CHAT_MIN_SCORE = {$min}. Rows under it are not returned to users.");
        $this->line('Set CHAT_MIN_SCORE a little below the lowest raw score that is still clearly relevant,');
        $this->line('then run: php artisan config:clear');

        return self::SUCCESS;
    }
}
