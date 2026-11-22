<?php

return [
    'mistral' => [
        'base_url'    => env('MISTRAL_BASE_URL', 'https://api.mistral.ai/v1'),
        'chat_model'  => env('MISTRAL_CHAT_MODEL', 'mistral-small-latest'),
        'embed_model' => env('MISTRAL_EMBED_MODEL', 'mistral-embed'),
        'embed_dim'   => (int) env('MISTRAL_EMBED_DIM', 1024),

        // Operator key: used ONLY by `php artisan jobs:embed` to index jobs.
        // Visitors use their own key for chatting; it is never stored.
        'operator_key' => env('MISTRAL_API_KEY', ''),
    ],

    'qdrant' => [
        'url'        => env('QDRANT_URL', 'http://127.0.0.1:6333'),
        'collection' => env('QDRANT_COLLECTION', 'jobs'),
        'api_key'    => env('QDRANT_API_KEY', ''),
    ],

    // Cosine similarity a job must reach to be returned by the vector search (0.60 = 60%).
    'min_score'    => (float) env('CHAT_MIN_SCORE', 0.60),
    'candidates'   => (int) env('CHAT_CANDIDATES', 40),
    'max_results'  => (int) env('CHAT_MAX_RESULTS', 5),
    'rate_per_min' => (int) env('CHAT_RATE_PER_MIN', 20),

    // Hybrid search: also run the keyword index and fuse both rankings (RRF).
    'hybrid'       => (bool) env('CHAT_HYBRID', true),
    'rrf_k'        => (int) env('CHAT_RRF_K', 60),

    // LLM re-ranking of the best candidates.
    'rerank'       => (bool) env('CHAT_RERANK', true),
    'rerank_pool'  => (int) env('CHAT_RERANK_POOL', 15),
    'rerank_min'   => (int) env('CHAT_RERANK_MIN', 50),

    // Diversity: at most this many results from one company (soft limit).
    'per_company'  => (int) env('CHAT_PER_COMPANY', 2),
];
