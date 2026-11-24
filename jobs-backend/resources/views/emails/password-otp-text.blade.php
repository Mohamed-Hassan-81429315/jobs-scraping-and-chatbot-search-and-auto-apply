Please verify your identity, {{ $name }}.

We received a request to reset the password for your Applyra account.

Here is your Applyra password reset verification code:

{{ $code }}

This code is valid for {{ $minutes }} minutes and can only be used once.
@if (!empty($resetUrl))

Enter the code here: {{ $resetUrl }}
@endif

Please don't share this code with anyone: we'll never ask for it on the phone or via email.

If you didn't request this code, you can safely ignore this email. Your password will remain unchanged.

Thanks,
The Applyra Team
