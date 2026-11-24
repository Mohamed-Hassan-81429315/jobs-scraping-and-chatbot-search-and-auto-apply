<?php

// Read through config('openai.*') so it keeps working with `php artisan config:cache`.
return [
    'key' => env('OPENAI_API_KEY'),
    'base_url' => env('OPENAI_BASE_URL', 'https://api.openai.com/v1'),

    // Any chat-capable model ID from https://developers.openai.com/api/docs/models
    'model' => env('OPENAI_MODEL', 'gpt-5.4-mini'),

    'timeout' => (int) env('OPENAI_TIMEOUT', 30),

    // Reasoning models count thinking tokens inside this limit, so keep it generous.
    'max_output_tokens' => (int) env('OPENAI_MAX_OUTPUT_TOKENS', 2000),

    // Optional: minimal | low | medium | high (leave empty to use the model default).
    'reasoning_effort' => env('OPENAI_REASONING_EFFORT'),
];
