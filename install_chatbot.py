#!/usr/bin/env python3
"""
Installs the Hirelume job-search chatbot. Run from the project root
(the folder that contains jobs-backend and jobs-frontend):

    python3 install_chatbot.py

BACKEND   POST /api/chat  - understands requests like "remote python jobs this
          week", searches the existing Elasticsearch index and answers with the
          top matches. Results always come from the database, never invented.
FRONTEND  a floating chat button (bottom-right) that opens a chat panel on
          every page.

Files that already exist are backed up as <name>.prepatch first.
"""
import pathlib
import shutil
import sys

ROOT = pathlib.Path(".")
BACK = ROOT / "jobs-backend"
FRONT = ROOT / "jobs-frontend"

if not (BACK / "artisan").exists() or not (FRONT / "app" / "layout.js").exists():
    sys.exit("Run this from the project root (the folder that contains jobs-backend and jobs-frontend).")

FILES = {}

# =====================================================================
# BACKEND
# =====================================================================

FILES[BACK / "app/Http/Controllers/ChatController.php"] = r'''<?php

namespace App\Http\Controllers;

use App\Services\JobSearch;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Str;

class ChatController extends Controller
{
    private const PLATFORMS = [
        'linkedin'        => 'LinkedIn',
        'indeed'          => 'Indeed',
        'glassdoor'       => 'Glassdoor',
        'odoo'            => 'Odoo',
        'smartrecruiters' => 'SmartRecruiters',
        'epam'            => 'EPAM',
        'remoteok'        => 'RemoteOK',
        'remotive'        => 'Remotive',
        'arbeitnow'       => 'Arbeitnow',
    ];

    private const STOPWORDS = [
        'a', 'an', 'the', 'i', 'me', 'my', 'we', 'you', 'is', 'are', 'am', 'can', 'could', 'would', 'please',
        'find', 'show', 'search', 'get', 'give', 'list', 'look', 'looking', 'want', 'need', 'any', 'some',
        'job', 'jobs', 'position', 'positions', 'role', 'roles', 'opening', 'openings', 'vacancy', 'vacancies',
        'work', 'for', 'in', 'at', 'near', 'around', 'on', 'of', 'to', 'with', 'from', 'and', 'available',
        'latest', 'newest', 'recent', 'new', 'there', 'do', 'have', 'has', 'about', 'related', 'that',
    ];

    public function message(Request $request, JobSearch $search): JsonResponse
    {
        $data  = $request->validate(['message' => ['required', 'string', 'max:300']]);
        $text  = trim((string) preg_replace('/\s+/u', ' ', $data['message']));
        $lower = Str::lower($text);

        if (preg_match('/^(hi|hello|hey|hola|salam|help|start|menu)\b/u', $lower)
            || str_contains($lower, 'what can you do')) {
            return $this->reply(
                "Hi! I can search every job in our database for you. Tell me a job title, skill, company or city, "
                . "and optionally a platform, \"remote\", or how recent the job should be.\n\n"
                . 'Try: remote Python jobs this week, Odoo developer, or data analyst in Berlin.'
            );
        }

        if (preg_match('/\b(thanks|thank you|thx)\b/u', $lower)) {
            return $this->reply('You are welcome! Ask me for another search any time.');
        }

        [$q, $source, $posted, $remote, $notes] = $this->parse($lower);

        if ($q === '' && $source === '' && $posted === '' && !$remote) {
            return $this->reply('What should I look for? Give me a job title, skill, company or city, for example "React developer in Cairo".');
        }

        try {
            $result = $search->search([
                'q'      => $q,
                'source' => $source,
                'posted' => $posted,
                'remote' => $remote ? '1' : '',
                'sort'   => $q === '' ? 'newest' : '',
                'page'   => 1,
            ]);
        } catch (\Throwable $e) {
            report($e);

            return $this->reply('The job search is temporarily unavailable. Please try again in a moment.');
        }

        $total = (int) ($result['total'] ?? 0);
        $what  = $q !== '' ? "“{$q}”" : 'that';
        $extra = $notes ? ' (' . implode(', ', $notes) . ')' : '';

        if ($total === 0) {
            return $this->reply(
                "I could not find jobs for {$what}{$extra}. Try fewer words or a related title, "
                . 'for example "developer" instead of "senior full-stack developer".'
            );
        }

        $top = array_map(fn ($j) => [
            'id'           => $j['id'],
            'title'        => $j['title'],
            'company'      => $j['company'],
            'location'     => $j['location'],
            'url'          => $j['url'],
            'source'       => $j['source'],
            'source_label' => self::PLATFORMS[$j['source']] ?? $j['source'],
            'posted_at'    => $j['posted_at'],
        ], array_slice($result['data'] ?? [], 0, 5));

        $query = array_filter([
            'q'      => $q,
            'source' => $source,
            'posted' => $posted,
            'remote' => $remote ? '1' : '',
        ], fn ($v) => $v !== '');

        $count = number_format($total);
        $word  = $total === 1 ? 'job' : 'jobs';
        $shown = count($top);

        return response()->json([
            'reply'      => "I found {$count} {$word} for {$what}{$extra}. Here " . ($shown === 1 ? 'is the top match:' : "are the top {$shown}:"),
            'jobs'       => $top,
            'total'      => $total,
            'search_url' => $query ? '/?' . http_build_query($query) : '/',
        ]);
    }

    /** @return array{0:string,1:string,2:string,3:bool,4:array<int,string>} */
    private function parse(string $lower): array
    {
        $rest   = ' ' . $lower . ' ';
        $source = '';
        $posted = '';
        $remote = false;
        $notes  = [];

        foreach (self::PLATFORMS as $key => $label) {
            $pattern = '/\b' . preg_quote($key, '/') . '\b/u';
            if (preg_match($pattern, $rest)) {
                $source  = $key;
                $notes[] = 'on ' . $label;
                $rest    = (string) preg_replace($pattern, ' ', $rest);
                break;
            }
        }

        $remotePattern = '/\b(remote|remotely|work from home|wfh|home ?office)\b/u';
        if (preg_match($remotePattern, $rest)) {
            $remote  = true;
            $notes[] = 'remote';
            $rest    = (string) preg_replace($remotePattern, ' ', $rest);
        }

        $windows = [
            '24h' => ['/\b(today|last 24 hours|past 24 hours|24 hours|24h|last day|past day)\b/u', 'posted in the last 24 hours'],
            '7d'  => ['/\b(this week|past week|last week|last 7 days|past 7 days|7 days)\b/u', 'posted in the last 7 days'],
            '30d' => ['/\b(this month|past month|last month|last 30 days|past 30 days|30 days)\b/u', 'posted in the last 30 days'],
        ];
        foreach ($windows as $key => [$pattern, $note]) {
            if (preg_match($pattern, $rest)) {
                $posted  = $key;
                $notes[] = $note;
                $rest    = (string) preg_replace($pattern, ' ', $rest);
                break;
            }
        }

        $words = [];
        $parts = preg_split('/\s+/u', trim($rest), -1, PREG_SPLIT_NO_EMPTY);
        foreach ($parts ?: [] as $word) {
            $word = trim($word, ',;:!?"()[]');
            if ($word === '' || in_array($word, self::STOPWORDS, true)) {
                continue;
            }
            $words[] = $word;
        }

        return [implode(' ', array_slice($words, 0, 8)), $source, $posted, $remote, $notes];
    }

    private function reply(string $text): JsonResponse
    {
        return response()->json([
            'reply'      => $text,
            'jobs'       => [],
            'total'      => 0,
            'search_url' => null,
        ]);
    }
}
'''

# =====================================================================
# FRONTEND
# =====================================================================

FILES[FRONT / "components/chat/ChatWidget.js"] = r'''"use client";

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';

const STORAGE_KEY = 'hirelume:chat';
const SUGGESTIONS = [
  'Remote Python jobs',
  'Odoo developer jobs',
  'Jobs posted this week',
  'Data analyst in Berlin',
];
const WELCOME = {
  role: 'bot',
  text: 'Hi! I search every job in our database for you. Tell me a title, skill, company or city, for example “remote React jobs in Berlin”.',
  jobs: [],
};

function safeUrl(url) {
  try {
    const u = new URL(url);
    return u.protocol === 'http:' || u.protocol === 'https:' ? u.href : null;
  } catch {
    return null;
  }
}

function ChatIcon() {
  return (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12Z" />
      <path d="M9 11h6M9 14h3" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true">
      <path d="M6 6l12 12M18 6 6 18" />
    </svg>
  );
}

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([WELCOME]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);
  const inputRef = useRef(null);

  // Restore the conversation for this browser tab.
  useEffect(() => {
    try {
      const saved = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || 'null');
      if (Array.isArray(saved) && saved.length) setMessages(saved.slice(-30));
    } catch {}
  }, []);

  useEffect(() => {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-30)));
    } catch {}
  }, [messages]);

  useEffect(() => {
    if (open) {
      endRef.current?.scrollIntoView({ block: 'end' });
      inputRef.current?.focus();
    }
  }, [open, messages, busy]);

  async function send(raw) {
    const text = raw.trim();
    if (!text || busy) return;

    setMessages((m) => [...m, { role: 'user', text }]);
    setInput('');
    setBusy(true);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ message: text }),
      });
      const data = await res.json().catch(() => null);

      if (!res.ok || !data?.reply) {
        throw new Error('bad response');
      }
      setMessages((m) => [
        ...m,
        { role: 'bot', text: data.reply, jobs: data.jobs || [], total: data.total || 0, searchUrl: data.search_url },
      ]);
    } catch {
      setMessages((m) => [
        ...m,
        { role: 'bot', text: 'Sorry, I could not reach the search service. Please try again in a moment.', jobs: [] },
      ]);
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setMessages([WELCOME]);
    try {
      sessionStorage.removeItem(STORAGE_KEY);
    } catch {}
  }

  const onlyWelcome = messages.length === 1;

  return (
    <>
      {open && (
        <section
          id="chat-panel"
          className="cb-panel"
          role="dialog"
          aria-label="Job search assistant"
          onKeyDown={(e) => {
            if (e.key === 'Escape') setOpen(false);
          }}
        >
          <header className="cb-head">
            <span className="cb-avatar" aria-hidden="true"><ChatIcon /></span>
            <div className="cb-title">
              <strong>Job assistant</strong>
              <span>Searches our live job database</span>
            </div>
            <button type="button" className="cb-icon" onClick={reset} title="Start a new chat">New</button>
            <button type="button" className="cb-icon" onClick={() => setOpen(false)} aria-label="Close chat">
              <CloseIcon />
            </button>
          </header>

          <div className="cb-body" role="log" aria-live="polite" aria-relevant="additions">
            {messages.map((m, i) => (
              <div key={i} className={m.role === 'user' ? 'cb-row user' : 'cb-row'}>
                <div className={m.role === 'user' ? 'cb-bubble user' : 'cb-bubble'}>
                  {m.text.split('\n').map((line, k) => (
                    <p key={k}>{line}</p>
                  ))}

                  {m.jobs?.length > 0 && (
                    <ul className="cb-jobs">
                      {m.jobs.map((j) => {
                        const href = safeUrl(j.url);
                        return (
                          <li key={j.id}>
                            {href ? (
                              <a className="cb-job" href={href} target="_blank" rel="nofollow noopener noreferrer">
                                <span className="cb-job-title">{j.title}</span>
                                <span className="cb-job-meta">
                                  {j.company}
                                  {j.location ? ` · ${j.location}` : ''}
                                </span>
                                <span className="cb-job-tag">{j.source_label}</span>
                              </a>
                            ) : (
                              <span className="cb-job">
                                <span className="cb-job-title">{j.title}</span>
                                <span className="cb-job-meta">{j.company}</span>
                              </span>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  )}

                  {m.searchUrl && m.total > (m.jobs?.length || 0) && (
                    <Link className="cb-more" href={m.searchUrl} prefetch={false} onClick={() => setOpen(false)}>
                      See all {m.total.toLocaleString('en-US')} results →
                    </Link>
                  )}
                </div>
              </div>
            ))}

            {busy && (
              <div className="cb-row">
                <div className="cb-bubble cb-typing" aria-label="The assistant is typing">
                  <span /><span /><span />
                </div>
              </div>
            )}

            {onlyWelcome && !busy && (
              <ul className="cb-suggest" aria-label="Suggestions">
                {SUGGESTIONS.map((s) => (
                  <li key={s}>
                    <button type="button" onClick={() => send(s)}>{s}</button>
                  </li>
                ))}
              </ul>
            )}
            <div ref={endRef} />
          </div>

          <form
            className="cb-form"
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
          >
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask for jobs, e.g. remote Python jobs"
              aria-label="Your message"
              maxLength={300}
              autoComplete="off"
              enterKeyHint="send"
            />
            <button type="submit" disabled={busy || !input.trim()} aria-label="Send message">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M5 12h14M13 6l6 6-6 6" />
              </svg>
            </button>
          </form>
        </section>
      )}

      <button
        type="button"
        className="cb-launch"
        onClick={() => setOpen(!open)}
        aria-label={open ? 'Close job assistant' : 'Open job assistant'}
        aria-expanded={open}
        aria-controls="chat-panel"
      >
        {open ? <CloseIcon /> : <ChatIcon />}
      </button>
    </>
  );
}
'''

CSS_MARK = "/* chat widget */"
CSS = r'''
/* chat widget */
.cb-launch { position: fixed; right: 20px; bottom: calc(20px + env(safe-area-inset-bottom, 0px)); z-index: 70; width: 60px; height: 60px; border-radius: 50%; border: 0; cursor: pointer; display: grid; place-items: center; color: #06101f; background: linear-gradient(135deg, var(--accent), var(--accent2)); box-shadow: 0 14px 40px -10px rgba(94, 234, 212, .55), 0 6px 20px rgba(0, 0, 0, .45); transition: transform .15s, filter .15s; }
.cb-launch:hover { transform: translateY(-2px) scale(1.04); filter: brightness(1.06); }

.cb-panel { position: fixed; right: 20px; bottom: calc(92px + env(safe-area-inset-bottom, 0px)); z-index: 70; width: min(400px, calc(100vw - 24px)); height: min(620px, calc(100vh - 130px)); display: flex; flex-direction: column; overflow: hidden; border-radius: 22px; background: #0b1020; border: 1px solid var(--line); box-shadow: 0 40px 100px -20px rgba(0, 0, 0, .8); animation: cb-in .18s ease-out; }
@keyframes cb-in { from { opacity: 0; transform: translateY(10px) scale(.98); } to { opacity: 1; transform: none; } }

.cb-head { display: flex; align-items: center; gap: 12px; padding: 14px 14px 14px 16px; border-bottom: 1px solid var(--line); background: linear-gradient(135deg, rgba(94, 234, 212, .12), rgba(129, 140, 248, .16)); }
.cb-avatar { width: 38px; height: 38px; border-radius: 12px; display: grid; place-items: center; color: #06101f; background: linear-gradient(135deg, var(--accent), var(--accent2)); }
.cb-avatar svg { width: 22px; height: 22px; }
.cb-title { flex: 1; min-width: 0; display: flex; flex-direction: column; line-height: 1.25; }
.cb-title strong { font-family: var(--font-display), sans-serif; font-size: 1rem; }
.cb-title span { font-size: .76rem; color: var(--muted); }
.cb-icon { border: 0; cursor: pointer; min-width: 34px; height: 34px; padding: 0 10px; border-radius: 10px; display: grid; place-items: center; font-size: .8rem; color: var(--muted); background: rgba(255, 255, 255, .06); }
.cb-icon:hover { color: var(--text); background: rgba(255, 255, 255, .12); }

.cb-body { flex: 1; overflow-y: auto; padding: 16px 14px; display: flex; flex-direction: column; gap: 12px; scroll-behavior: smooth; }
.cb-row { display: flex; }
.cb-row.user { justify-content: flex-end; }
.cb-bubble { max-width: 88%; padding: 11px 14px; border-radius: 16px 16px 16px 4px; font-size: .92rem; line-height: 1.5; background: rgba(255, 255, 255, .07); border: 1px solid var(--line); overflow-wrap: anywhere; }
.cb-bubble p + p { margin-top: 8px; }
.cb-bubble.user { border: 0; border-radius: 16px 16px 4px 16px; color: #06101f; font-weight: 500; background: linear-gradient(135deg, var(--accent), var(--accent2)); }

.cb-jobs { display: grid; gap: 8px; margin-top: 12px; }
.cb-job { display: grid; gap: 2px; padding: 10px 12px; border-radius: 12px; background: rgba(8, 12, 26, .65); border: 1px solid var(--line); transition: border-color .15s, transform .15s; }
a.cb-job:hover { border-color: rgba(94, 234, 212, .6); transform: translateY(-1px); }
.cb-job-title { font-weight: 600; font-size: .9rem; line-height: 1.3; }
.cb-job-meta { font-size: .8rem; color: var(--muted); }
.cb-job-tag { justify-self: start; margin-top: 4px; padding: 2px 9px; border-radius: 999px; font-size: .68rem; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; background: rgba(129, 140, 248, .2); color: #c7d2fe; }
.cb-more { display: inline-block; margin-top: 12px; font-size: .85rem; font-weight: 600; color: var(--accent); }
.cb-more:hover { text-decoration: underline; text-underline-offset: 3px; }

.cb-suggest { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 4px; }
.cb-suggest button { cursor: pointer; padding: 8px 14px; border-radius: 999px; font-size: .84rem; color: #d5dbf2; background: var(--panel); border: 1px solid var(--line); }
.cb-suggest button:hover { border-color: rgba(94, 234, 212, .6); color: var(--text); }

.cb-typing { display: flex; gap: 5px; align-items: center; padding: 14px; }
.cb-typing span { width: 7px; height: 7px; border-radius: 50%; background: var(--muted); animation: cb-dot 1s infinite ease-in-out; }
.cb-typing span:nth-child(2) { animation-delay: .15s; }
.cb-typing span:nth-child(3) { animation-delay: .3s; }
@keyframes cb-dot { 0%, 80%, 100% { opacity: .3; transform: translateY(0); } 40% { opacity: 1; transform: translateY(-3px); } }

.cb-form { display: flex; gap: 8px; padding: 12px; border-top: 1px solid var(--line); background: #0e1328; }
.cb-form input { flex: 1; min-width: 0; padding: 12px 14px; border-radius: 14px; border: 1px solid var(--line); background: rgba(255, 255, 255, .05); color: var(--text); font: inherit; font-size: .92rem; outline: none; }
.cb-form input:focus { border-color: rgba(94, 234, 212, .7); box-shadow: 0 0 0 3px rgba(94, 234, 212, .14); }
.cb-form button { width: 46px; border: 0; border-radius: 14px; cursor: pointer; display: grid; place-items: center; color: #06101f; background: linear-gradient(135deg, var(--accent), var(--accent2)); }
.cb-form button:disabled { opacity: .4; cursor: not-allowed; }

@media (max-width: 520px) {
  .cb-panel { right: 12px; left: 12px; width: auto; bottom: calc(86px + env(safe-area-inset-bottom, 0px)); height: calc(100vh - 110px); }
  .cb-launch { right: 14px; bottom: calc(14px + env(safe-area-inset-bottom, 0px)); }
}
'''

# =====================================================================
# Apply (verify every patch first; write only if all succeed)
# =====================================================================

problems = []
patched = {}


def plan(path, pairs, skip_marker):
    if not path.exists():
        problems.append(f"{path}: file not found")
        return
    text = path.read_text(encoding="utf-8")
    if skip_marker in text:
        return  # already patched
    for old, new in pairs:
        if text.count(old) != 1:
            problems.append(f"{path}: expected 1 match, found {text.count(old)} for: {old[:70]!r}")
        else:
            text = text.replace(old, new)
    patched[path] = text


plan(
    FRONT / "app/layout.js",
    [
        ("import UserMenu from '../components/UserMenu';",
         "import UserMenu from '../components/UserMenu';\nimport ChatWidget from '../components/chat/ChatWidget';"),
        ('<footer className="site-footer">',
         '<ChatWidget />\n\n        <footer className="site-footer">'),
    ],
    "ChatWidget",
)

plan(
    BACK / "routes/api.php",
    [
        ("use App\\Http\\Controllers\\AuthController;",
         "use App\\Http\\Controllers\\AuthController;\nuse App\\Http\\Controllers\\ChatController;"),
        ("Route::get('/suggest', [JobController::class, 'suggest']);",
         "Route::get('/suggest', [JobController::class, 'suggest']);\n"
         "Route::post('/chat', [ChatController::class, 'message'])->middleware('throttle:30,1');"),
    ],
    "ChatController",
)

css_path = FRONT / "app/globals.css"
if not css_path.exists():
    problems.append("app/globals.css not found")

if problems:
    print("Nothing was changed. Problems found:")
    for p in problems:
        print("  -", p)
    print("\nIf layout.js or routes/api.php differ from what the installer expects,")
    print("send me the problem lines and I will adjust it.")
    sys.exit(1)

written = []
for path, content in FILES.items():
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_name(path.name + ".prepatch")
        if not backup.exists():
            shutil.copy2(path, backup)
    path.write_text(content, encoding="utf-8")
    written.append(str(path))

for path, text in patched.items():
    backup = path.with_name(path.name + ".prepatch")
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(text, encoding="utf-8")
    written.append(str(path))

css_text = css_path.read_text(encoding="utf-8")
if CSS_MARK not in css_text:
    backup = css_path.with_name(css_path.name + ".prepatch")
    if not backup.exists():
        shutil.copy2(css_path, backup)
    with css_path.open("a", encoding="utf-8") as handle:
        handle.write(CSS)
    written.append(str(css_path))

print(f"Installed {len(written)} files:")
for item in written:
    print("  +", item)
print("\nNext: restart the backend and frontend, then look for the round chat button at the bottom-right.")
