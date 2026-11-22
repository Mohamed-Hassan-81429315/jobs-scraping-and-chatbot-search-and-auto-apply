<?php

return [
    'openai' => [
        'base_url'    => env('OPENAI_BASE_URL', 'https://api.openai.com/v1'),
        'chat_model'  => env('OPENAI_CHAT_MODEL', 'gpt-4o-mini'),
        'embed_model' => env('OPENAI_EMBED_MODEL', 'text-embedding-3-small'),
        // text-embedding-3-small = 1536, text-embedding-3-large = 3072 (or any smaller size you choose).
        'embed_dim'   => (int) env('OPENAI_EMBED_DIM', 1536),

        // Operator key: used ONLY by `php artisan jobs:embed` to index jobs.
        // Visitors use their own key for chatting; it is never stored.
        'operator_key' => env('OPENAI_API_KEY', ''),
    ],

    'qdrant' => [
        'url'        => env('QDRANT_URL', 'http://127.0.0.1:6333'),
        // A separate collection per embedding model: vectors from different models are not comparable.
        'collection' => env('QDRANT_COLLECTION', 'jobs_openai'),
        'api_key'    => env('QDRANT_API_KEY', ''),
    ],

    // Minimum cosine similarity for the vector search. OpenAI embeddings score LOWER than
    // most other models (a good match is often 0.40 to 0.60), so 0.60 would hide almost everything.
    // The LLM re-ranker removes weak matches afterwards.
    'min_score'    => (float) env('CHAT_MIN_SCORE', 0.35),
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
