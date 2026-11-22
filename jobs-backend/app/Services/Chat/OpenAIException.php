<?php

namespace App\Services\Chat;

class OpenAIException extends \RuntimeException
{
    /**
     * reason:
     *   invalid_key   401, the key is wrong or revoked
     *   forbidden     403, the key lacks permission or region/model access
     *   quota         429 insufficient_quota, no credit left
     *   rate_limited  429, too many requests right now
     *   model         404, the configured model does not exist for this key
     *   bad_json      the model did not return valid JSON
     *   upstream      any other OpenAI error
     *   network       OpenAI could not be reached
     */
    public function __construct(string $message, public readonly string $reason = 'upstream', int $status = 502)
    {
        parent::__construct($message, $status);
    }
}
