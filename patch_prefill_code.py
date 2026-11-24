#!/usr/bin/env python3
"""
Email button -> /reset-password?email=...&code=123456 -> the 6-digit box is already filled.

Run from the project root:  python3 patch_prefill_code.py

What it does
  - reset-password page: reads ?code= (only exactly 6 digits are accepted) and hands it to the form
  - form: pre-fills the code box, then removes the code from the address bar so it does not stay in
    browser history; the page also sends no Referer header
  - the link itself never uses up the code (only submitting the form does), so mail-scanner
    pre-fetching a link cannot burn it

Each file is backed up as <name>.prepatch. If a file no longer matches what this script expects,
it is left untouched and the script tells you which edit to make by hand.
"""

import pathlib
import shutil
import sys

FRONT = pathlib.Path("jobs-frontend")
if not (FRONT / "app").exists():
    sys.exit("Run this from the project root (the folder that contains jobs-frontend).")

PAGE = FRONT / "app/reset-password/page.js"
FORM = FRONT / "components/auth/ResetOtpForm.js"

problems = []


def edit(path, pairs, marker):
    if not path.exists():
        problems.append(f"{path}: file not found")
        return
    text = path.read_text(encoding="utf-8")
    if marker in text:
        print(f"already  {path}")
        return
    new = text
    for old, repl, what in pairs:
        if old not in new:
            problems.append(f"{path}: could not find the place to {what}")
            return
        new = new.replace(old, repl, 1)
    bak = path.with_name(path.name + ".prepatch")
    if not bak.exists():
        shutil.copy2(path, bak)
    path.write_text(new, encoding="utf-8")
    print(f"patched  {path}")


# ---------------------------------------------------------------- page
edit(
    PAGE,
    [
        (
            "  robots: { index: false, follow: false },\n",
            "  robots: { index: false, follow: false },\n"
            "  referrer: 'no-referrer', // the address may carry a one-time code: never leak it\n",
            "add referrer: 'no-referrer' to metadata",
        ),
        (
            "  if (!EMAIL.test(email)) redirect('/forgot-password');\n",
            "  if (!EMAIL.test(email)) redirect('/forgot-password');\n\n"
            "  // The email button adds ?code=123456. Only exactly six digits are accepted.\n"
            "  const rawCode = String(sp?.code ?? '').trim();\n"
            "  const code = /^\\d{6}$/.test(rawCode) ? rawCode : '';\n",
            "read the code from the address",
        ),
        (
            "<ResetOtpForm email={email} />",
            "<ResetOtpForm email={email} initialCode={code} />",
            "pass the code to the form",
        ),
    ],
    "initialCode={code}",
)

# ---------------------------------------------------------------- form
edit(
    FORM,
    [
        (
            "import { useActionState } from 'react';",
            "import { useActionState, useEffect } from 'react';",
            "import useEffect",
        ),
        (
            "export default function ResetOtpForm({ email }) {",
            "export default function ResetOtpForm({ email, initialCode = '' }) {",
            "accept the initialCode prop",
        ),
        (
            "  const top = state.error || state.errors.email;\n",
            "  const top = state.error || state.errors.email;\n\n"
            "  // The code came from the email link: take it out of the address bar (history, screenshots).\n"
            "  useEffect(() => {\n"
            "    if (!initialCode) return;\n"
            "    const url = new URL(window.location.href);\n"
            "    if (url.searchParams.has('code')) {\n"
            "      url.searchParams.delete('code');\n"
            "      window.history.replaceState(null, '', url.pathname + url.search);\n"
            "    }\n"
            "  }, [initialCode]);\n",
            "add the effect that removes the code from the address bar",
        ),
        (
            "        defaultValue={state.values.code}\n        error={state.errors.code}\n        autoFocus\n",
            "        defaultValue={state.values.code ?? initialCode}\n        error={state.errors.code}\n        autoFocus={!initialCode}\n",
            "pre-fill the code box",
        ),
    ],
    "initialCode",
)

if problems:
    print("\nNeeds a manual edit:")
    for p in problems:
        print(" -", p)
    sys.exit(1)

print("\nDone. Now make the email button point at /reset-password?email=...&code=...  (see the instructions).")
