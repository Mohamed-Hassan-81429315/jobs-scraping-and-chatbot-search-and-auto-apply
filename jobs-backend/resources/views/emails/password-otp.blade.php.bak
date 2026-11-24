<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <meta name="supported-color-schemes" content="light">
  <title>Your Applyra password reset verification code</title>
</head>
<body style="margin:0;padding:0;background:#ffffff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#1f2328;">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">
    Your Applyra password reset verification code is {{ $code }}. It expires in {{ $minutes }} minutes.
  </div>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#ffffff;">
    <tr>
      <td align="center" style="padding:32px 16px 40px;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:480px;">

          <!-- Logo -->
          <tr>
            <td align="center" style="padding:8px 0 20px;">
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

          <!-- Heading -->
          <tr>
            <td align="center" style="padding:0 0 22px;">
              <h1 style="margin:0;font-size:24px;line-height:1.35;font-weight:400;color:#1f2328;">
                Please verify your identity, <strong>{{ $name }}</strong>
              </h1>
            </td>
          </tr>

          <!-- Code box -->
          <tr>
            <td style="padding:0;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border:1px solid #d0d7de;border-radius:6px;">
                <tr>
                  <td style="padding:16px 18px 18px;">
                    <p style="margin:0 0 14px;font-size:14px;line-height:1.5;color:#1f2328;">
                      Here is your Applyra password reset verification code:
                    </p>
                    <p style="margin:0 0 18px;text-align:center;font-family:Menlo,Consolas,'Courier New',monospace;font-size:30px;line-height:1.3;font-weight:600;letter-spacing:7px;color:#1f2328;-webkit-user-select:all;user-select:all;">{{ $code }}</p>
                    @if (!empty($resetUrl))
                    <table role="presentation" align="center" cellspacing="0" cellpadding="0" border="0" style="margin:0 auto 18px;">
                      <tr>
                        <td align="center" bgcolor="#4f46e5" style="border-radius:999px;background:#4f46e5;">
                          <a href="{{ $resetUrl }}" target="_blank" rel="noopener" style="display:inline-block;padding:11px 24px;font-size:14px;font-weight:600;line-height:1.2;color:#ffffff;text-decoration:none;border-radius:999px;">Enter code on Applyra</a>
                        </td>
                      </tr>
                    </table>
                    @endif
                    <p style="margin:0 0 14px;font-size:14px;line-height:1.5;color:#1f2328;">
                      This code is valid for <strong>{{ $minutes }} minutes</strong> and can only be used once.
                    </p>
                    <p style="margin:0 0 14px;font-size:14px;line-height:1.5;color:#1f2328;">
                      <strong>Please don't share this code with anyone:</strong> we'll never ask for it on the phone or via email.
                    </p>
                    <p style="margin:0;font-size:14px;line-height:1.5;color:#1f2328;">
                      Thanks,<br>The Applyra Team
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:18px 2px 0;font-size:12px;line-height:1.5;color:#656d76;">
              You're receiving this email because a verification code was requested for your Applyra account. If this wasn't you, please ignore this email and your password will stay unchanged.
            </td>
          </tr>
          <tr>
            <td style="padding:14px 2px 0;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"><tr><td style="border-top:1px solid #d0d7de;font-size:0;line-height:0;height:1px;">&nbsp;</td></tr></table>
            </td>
          </tr>
          <tr>
            <td align="center" style="padding:22px 12px 0;font-size:11px;line-height:1.5;color:#8c959f;">
              Applyra &middot; Automated message, please do not reply.
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
