<?php

namespace App\Services\Chat;

class MistralException extends \RuntimeException
{
    /** reason: invalid_key | rate_limited | bad_json | upstream | network */
    public function __construct(string $message, public readonly string $reason = 'upstream', int $status = 502)
    {
        parent::__construct($message, $status);
    }
}
