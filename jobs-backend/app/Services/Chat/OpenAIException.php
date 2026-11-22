<?php

namespace App\Services\Chat;

class OpenAIException extends \RuntimeException
{
    /**
     * reason: invalid_key | quota | rate_limited | model | forbidden
     *         | bad_json | refused | upstream | network
     */
    public function __construct(string $message, public readonly string $reason = 'upstream', int $status = 502)
    {
        parent::__construct($message, $status);
    }
}
