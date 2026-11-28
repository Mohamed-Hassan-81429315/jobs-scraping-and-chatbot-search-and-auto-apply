#!/usr/bin/env python3
"""Run from the folder holding jobs-backend and jobs-frontend (after apply_autofill.py):
     python3 apply_one_tab.py        (needs otp-handoff.js next to this script)
Makes the email button hand the code to the ORIGINAL tab instead of continuing in the new one."""
import re, pathlib, shutil, sys
here = pathlib.Path(__file__).resolve().parent
root = pathlib.Path('.')
def edit(rel, fn, label):
    p = root / rel
    if not p.exists(): print(f'SKIP  {rel} (not found)'); return
    s = p.read_text(); n = fn(s)
    if n is None: print(f'FAIL  {label}: pattern not found in {rel}'); return
    if n == s: print(f'OK    {label}: already applied'); return
    p.with_suffix(p.suffix + '.prepatch2').write_text(s); p.write_text(n); print(f'DONE  {label}')

lib = root / 'jobs-frontend/lib/otp-handoff.js'
lib.write_text((here / 'otp-handoff.js').read_text()); print('DONE  jobs-frontend/lib/otp-handoff.js')

NEW_EFFECT = """  // The email button opens a NEW tab at /reset-password?email=...#code=123456.
  // 1) If the tab where the code was requested is still open, hand the code to it and let this
  //    tab close (the user stays in one tab). 2) Otherwise fill the code here.
  // Fragment and hand-off never reach a server; the address bar is cleaned right away.
  const [handedOff, setHandedOff] = useState(false);
  useEffect(() => {
    const fill = (c) => {
      const input = document.getElementById('code');
      if (input) input.value = c;
      document.getElementById('password')?.focus();
    };
    const m = /(?:^#|&)code=(\\d{6})(?:&|$)/.exec(window.location.hash);
    if (m) window.history.replaceState(null, '', window.location.pathname + window.location.search);
    const stashed = m ? '' : takeStashedCode(email);

    const stop = listenForCode(email, fill); // this tab is the original and a new tab sent a code
    if (m) {
      sendCode(email, m[1]).then((accepted) => {
        if (accepted) { setHandedOff(true); window.close(); } else fill(m[1]);
      });
    } else if (stashed) {
      fill(stashed);
    }
    return stop;
  }, [email]);
"""
NOTICE = """  if (handedOff) {
    return (
      <div className="auth-form" role="status">
        <p className="alert ok">Your code was sent to the tab you started in. Continue there, and close this one.</p>
        <button type="button" className="auth-submit" onClick={() => window.close()}>Close this tab</button>
      </div>
    );
  }

"""
def form(s):
    if 'listenForCode' in s: return s
    n = re.sub(r"import \{([^}]*)\} from 'react';",
               lambda m: m.group(0) if 'useState' in m.group(1) else "import {%s, useState } from 'react';" % m.group(1).rstrip(), s, count=1)
    n = n.replace("import SubmitButton from './SubmitButton';",
        "import SubmitButton from './SubmitButton';\nimport { listenForCode, sendCode, takeStashedCode } from '../../lib/otp-handoff';", 1)
    n, c = re.subn(r"  // The email button opens.*?\}, \[\]\);\n", lambda m: NEW_EFFECT, n, count=1, flags=re.S)
    if not c: return None
    n, c = re.subn(r"\n  return \(\n    <form", lambda m: "\n" + NOTICE + "  return (\n    <form", n, count=1)
    return n if c else None
edit('jobs-frontend/components/auth/ResetOtpForm.js', form, 'reset page: hand off / receive code')

LISTEN = """
  // The email button opens a new tab; that tab sends the code here. Move this same tab on to
  // the code screen (the dialog closes with it) instead of leaving the user in two tabs.
  useEffect(() => {
    if (!email || !sentAt) return undefined;
    return listenForCode(email, (code) => {
      stashCode(email, code);
      setDismissedSentAt(sentAt);
      const params = new URLSearchParams({ email, sentAt: String(latestSentAtRef.current || sentAt) });
      router.push(`/reset-password?${params.toString()}`);
      try { window.focus(); } catch {}
    });
  }, [email, sentAt, router]);
"""
def dialog(s):
    if 'listenForCode' in s: return s
    n = s.replace("import ResendCodeControl from './ResendCodeControl';",
        "import ResendCodeControl from './ResendCodeControl';\nimport { listenForCode, stashCode } from '../../lib/otp-handoff';", 1)
    n, c = re.subn(r"(\n  const handleResent = useCallback)", lambda m: LISTEN + m.group(1), n, count=1)
    return n if c else None
edit('jobs-frontend/components/auth/OtpSentDialog.js', dialog, 'dialog moves to code screen in the same tab')
print('\nRestart next dev, request a NEW code, keep the first tab open, click the email button.')
