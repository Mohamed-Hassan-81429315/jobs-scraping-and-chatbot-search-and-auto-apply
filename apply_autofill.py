#!/usr/bin/env python3
"""Run from the project root (the folder holding jobs-backend and jobs-frontend):
   python3 apply_autofill.py
Edits files by pattern, so it works even if you changed them. Safe to re-run."""
import re, sys, pathlib
root = pathlib.Path('.')
def edit(rel, fn, label):
    p = root / rel
    if not p.exists():
        print(f'SKIP  {rel} (not found)'); return
    s = p.read_text(); n = fn(s)
    if n is None: print(f'FAIL  {label}: pattern not found in {rel}'); return
    if n == s: print(f'OK    {label}: already applied'); return
    p.with_suffix(p.suffix + '.prepatch').write_text(s); p.write_text(n); print(f'DONE  {label}')

def mail(s):
    if "#code=" in s: return s
    n, c = re.subn(r"http_build_query\(\['email' => \$this->email\]\)\s*;",
        "http_build_query(['email' => $this->email])\n            . '#code=' . rawurlencode($this->code);", s)
    return n if c else None
edit('jobs-backend/app/Mail/PasswordOtpMail.php', mail, 'email link carries #code=')

def test(s):
    if '#code=' in s: return s
    n, c = re.subn(r"&&\s*preg_match\('~reset-password\[\^\"\]\*'[^\n]*\n", "", s)
    n = n.replace("str_contains($html, '/reset-password?email=sara%40example.com')",
                  "str_contains($html, '/reset-password?email=sara%40example.com#code=' . $mail->code)")
    n = n.replace("'name' => $mail->name,\n            ])->render();",
                  "'name' => $mail->name,\n                'resetUrl' => 'http://x.test/reset-password?email=a#code=' . $mail->code,\n            ])->render();")
    return n
edit('jobs-backend/tests/Feature/PasswordOtpMailTest.php', test, 'test expects fragment')

def field(s):
    if 'inputMode' in s: return s
    n = s.replace("  maxLength,\n", "  maxLength,\n  minLength,\n  inputMode,\n  pattern,\n", 1)
    n = re.sub(r"(\n(\s*)maxLength=\{maxLength\})", r"\1\n\2minLength={minLength}\n\2inputMode={inputMode}\n\2pattern={pattern}", n, count=1)
    return n if 'pattern={pattern}' in n else None
edit('jobs-frontend/components/auth/Field.js', field, 'Field forwards inputMode/pattern')

EFFECT = """
  // The email button opens /reset-password?email=...#code=123456. Read the code in the
  // browser, fill the box, then drop the fragment so it does not stay in history.
  useEffect(() => {
    const m = /(?:^#|&)code=(\\d{6})(?:&|$)/.exec(window.location.hash);
    if (!m) return;
    const input = document.getElementById('code');
    if (input && !input.value) input.value = m[1];
    window.history.replaceState(null, '', window.location.pathname + window.location.search);
    document.getElementById('password')?.focus();
  }, []);
"""
def form(s):
    if 'location.hash' in s: return s
    n = re.sub(r"import \{([^}]*)\} from 'react';",
               lambda m: m.group(0) if 'useEffect' in m.group(1) else "import {%s, useEffect } from 'react';" % m.group(1).rstrip(), s, count=1)
    n, c = re.subn(r"(const \[state, action\] = useActionState\([^\n]*\n)", lambda m: m.group(1) + EFFECT, n, count=1)
    return n if c else None
edit('jobs-frontend/components/auth/ResetOtpForm.js', form, 'reset page prefills the code')

def nextcfg(s):
    if 'allowedDevOrigins' in s: return s
    n, c = re.subn(r"(const nextConfig[^{]*\{\n)", r"\1  // Phones on your Wi-Fi: next dev blocks its JS bundles from non-localhost origins otherwise.\n  allowedDevOrigins: ['192.168.*.*', '10.*.*.*', '172.16.*.*', '*.local'],\n", s, count=1)
    return n if c else None
for f in ('next.config.ts', 'next.config.js', 'next.config.mjs'):
    if (root / 'jobs-frontend' / f).exists(): edit('jobs-frontend/' + f, nextcfg, 'allowedDevOrigins'); break

def env(s):
    return s if 'FRONTEND_URL' in s else s.rstrip('\n') + "\n\n# Where the reset email button sends people. On a phone use this PC's LAN address, not localhost.\nFRONTEND_URL=http://192.168.100.8:3000\n"
edit('jobs-backend/.env.example', env, '.env.example FRONTEND_URL')
print('\nNow set FRONTEND_URL=http://192.168.100.8:3000 in jobs-backend/.env, run php artisan config:clear, restart next dev.')
