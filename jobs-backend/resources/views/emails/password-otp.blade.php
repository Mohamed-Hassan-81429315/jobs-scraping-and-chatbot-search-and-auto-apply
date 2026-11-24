<!doctype html>
<html>
<body style="margin:0;padding:24px;background:#f4f6fb;font-family:Arial,Helvetica,sans-serif;color:#111827;">
  <div style="max-width:460px;margin:0 auto;background:#ffffff;border-radius:14px;padding:28px;">
    <h2 style="margin:0 0 8px;font-size:20px;">Your password reset code</h2>
    <p style="margin:0 0 4px;color:#374151;">Use this code to choose a new password on {{ config('app.name') }}:</p>
    <p style="margin:18px 0;font-size:36px;letter-spacing:10px;font-weight:700;">{{ $code }}</p>
    <p style="margin:0;color:#6b7280;font-size:14px;line-height:1.5;">
      It expires in {{ $minutes }} minutes. If you did not ask for it, ignore this email: your password stays the same.
      Never share this code with anyone.
    </p>
  </div>
</body>
</html>
