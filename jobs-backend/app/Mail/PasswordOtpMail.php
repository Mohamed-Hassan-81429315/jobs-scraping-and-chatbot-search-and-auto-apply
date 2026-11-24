<?php

namespace App\Mail;

use Illuminate\Bus\Queueable;
use Illuminate\Mail\Mailable;
use Illuminate\Mail\Mailables\Content;
use Illuminate\Mail\Mailables\Envelope;
use Illuminate\Queue\SerializesModels;

class PasswordOtpMail extends Mailable
{
    use Queueable, SerializesModels;

    // Not queued on purpose: the code must not be written into a jobs table.
    public function __construct(
        public string $code,
        public int $minutes,
        public string $name,
        public ?string $email = null,
    ) {
    }

    public function envelope(): Envelope
    {
        return new Envelope(subject: '[Applyra] Your password reset verification code');
    }

    public function content(): Content
    {
        return new Content(
            view: 'emails.password-otp',
            text: 'emails.password-otp-text',
            with: ['resetUrl' => $this->resetUrl()],
        );
    }

    /**
     * Button target: the "enter your code" page with the email already filled in.
     * The code travels in the URL fragment (#code=...), never the query string: browsers do not send
     * fragments to servers, proxies, access logs or Referer headers, and the page clears it on load.
     */
    private function resetUrl(): ?string
    {
        if (!$this->email) {
            return null;
        }

        $url = rtrim((string) config('app.frontend_url'), '/')
            . '/reset-password?'
            . http_build_query(['email' => $this->email]);

        return preg_match('/^\d{6}$/', $this->code) ? $url . '#code=' . $this->code : $url;
    }
}
