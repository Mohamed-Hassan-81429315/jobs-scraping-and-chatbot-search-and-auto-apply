<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>Your Applyra password reset verification code</title>
</head>
<body style="margin:0;padding:0;background:#f6f8fa;font-family:Arial,Helvetica,sans-serif;color:#1f2328;">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">
    Your Applyra password reset verification code is ready. It expires in {{ $minutes }} minutes.
  </div>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#f6f8fa;">
    <tr>
      <td align="center" style="padding:40px 16px;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:560px;">
          <tr>
            <td align="center" style="padding:0 0 24px;">
              <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <td align="center" valign="middle" width="40" height="40" style="width:40px;height:40px;">
                    <img src="{{ $message->embed(public_path('images/applyra-logo.png')) }}" width="40" height="40" alt="Applyra logo" style="display:block;width:40px;height:40px;border:0;border-radius:10px;">
                  </td>
                  <td style="padding-left:10px;color:#1f2328;font-size:21px;font-weight:700;letter-spacing:-0.4px;">Applyra</td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:30px 32px;background:#ffffff;border:1px solid #d8dee4;border-radius:12px;">
              <h1 style="margin:0 0 14px;font-size:24px;line-height:1.35;font-weight:600;color:#1f2328;">
                Please verify your identity, {{ $name }}
              </h1>
              <p style="margin:0 0 22px;font-size:15px;line-height:1.6;color:#424a53;">
                We received a request to reset the password for your Applyra account. Use the verification code below to continue.
              </p>
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border:1px solid #d8dee4;border-radius:8px;">
                <tr>
                  <td style="padding:20px 22px 22px;">
                    <p style="margin:0 0 12px;font-size:14px;line-height:1.5;color:#424a53;">
                      Here is your Applyra password reset verification code:
                    </p>
                    <p style="margin:0 0 18px;text-align:center;font-family:'Courier New',Courier,monospace;font-size:32px;line-height:1.4;font-weight:700;letter-spacing:8px;color:#1f2328;">
                      {{ $code }}
                    </p>
                    <p style="margin:0;font-size:14px;line-height:1.6;color:#424a53;">
                      This code is valid for <strong>{{ $minutes }} minutes</strong> and can only be used once.
                    </p>
                  </td>
                </tr>
              </table>
              <p style="margin:20px 0 10px;font-size:14px;line-height:1.6;color:#424a53;">
                <strong>Please don't share this code with anyone.</strong> Applyra will never ask you to provide it by phone or email.
              </p>
              <p style="margin:0;font-size:14px;line-height:1.6;color:#57606a;">
                If you didn't request this code, you can safely ignore this email. Your password will remain unchanged.
              </p>
              <p style="margin:22px 0 0;font-size:14px;line-height:1.6;color:#424a53;">
                Thanks,<br>The Applyra Team
              </p>
            </td>
          </tr>
          <tr>
            <td align="center" style="padding:18px 12px 0;font-size:12px;line-height:1.5;color:#6e7781;">
              This message was sent because a password reset was requested for an Applyra account.
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
