<?php

return [
    'openai' => [
        'base_url'    => env('OPENAI_BASE_URL', 'https://api.openai.com/v1'),
        'chat_model'  => env('OPENAI_CHAT_MODEL', 'gpt-5-mini'),
        'embed_model' => env('OPENAI_EMBED_MODEL', 'text-embedding-3-small'),
        'embed_dim'   => (int) env('OPENAI_EMBED_DIM', 1536),

        // Operator key: used ONLY by `php artisan jobs:embed` and `chat:doctor`.
        // Visitors chat with their own key; it is never stored.
        'operator_key' => env('OPENAI_API_KEY', ''),
    ],

    'qdrant' => [
        'url'        => env('QDRANT_URL', 'http://127.0.0.1:6333'),
        'collection' => env('QDRANT_COLLECTION', 'jobs_openai'),
        'api_key'    => env('QDRANT_API_KEY', ''),
    ],

    // Raw cosine similarity a job must reach to be returned. This is the "60%"
    // rule: scores at or above it are shown as 60% and up. The right raw value
    // depends on the embedding model: run `php artisan chat:doctor` to calibrate.
    'min_score'    => (float) env('CHAT_MIN_SCORE', 0.45),
    'candidates'   => (int) env('CHAT_CANDIDATES', 40),
    'max_results'  => (int) env('CHAT_MAX_RESULTS', 5),
    'rate_per_min' => (int) env('CHAT_RATE_PER_MIN', 20),
];
