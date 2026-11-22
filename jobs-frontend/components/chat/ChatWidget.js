"use client";

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';

const STORAGE_KEY = 'hirelume:chat:v3';
const SUGGESTIONS = [
  'Remote Python jobs',
  'Odoo developer jobs',
  'Senior data analyst in Berlin',
  'Jobs posted this week',
];
const STAGES = {
  planning: 'Understanding your request...',
  searching: 'Searching the job index...',
  ranking: 'Ranking the best matches...',
  writing: 'Writing the answer...',
};
const WELCOME = {
  role: 'bot',
  text: 'Hi! Tell me what kind of job you want, in your own words and any language, and I will find the best matches.',
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

/** Reads a server-sent-events response and calls onEvent(name, data) for each event. */
async function readEvents(res, onEvent) {
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let index;
    while ((index = buffer.indexOf('\n\n')) !== -1) {
      const block = buffer.slice(0, index);
      buffer = buffer.slice(index + 2);

      let event = 'message';
      let data = '';
      for (const line of block.split('\n')) {
        if (line.startsWith('event:')) event = line.slice(6).trim();
        else if (line.startsWith('data:')) data += line.slice(5).trim();
      }
      if (!data) continue;

      try {
        onEvent(event, JSON.parse(data));
      } catch {}
    }
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
  const [status, setStatus] = useState('checking'); // checking | needs_key | ready
  const [messages, setMessages] = useState([WELCOME]);
  const [lastSearch, setLastSearch] = useState(null);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState('');
  const [keyInput, setKeyInput] = useState('');
  const [keyBusy, setKeyBusy] = useState(false);
  const [keyError, setKeyError] = useState('');
  const endRef = useRef(null);
  const inputRef = useRef(null);

  // Restore the conversation for this browser tab (the API key is never stored here).
  useEffect(() => {
    try {
      const saved = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || 'null');
      if (saved && Array.isArray(saved.messages) && saved.messages.length) {
        const restored = saved.messages
          .filter((m) => !(m.pending && !m.text && !m.jobs?.length))
          .map((m) => ({ ...m, pending: false }))
          .slice(-30);
        if (restored.length) setMessages(restored);
        setLastSearch(saved.lastSearch || null);
      }
    } catch {}
  }, []);

  useEffect(() => {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ messages: messages.slice(-30), lastSearch }));
    } catch {}
  }, [messages, lastSearch]);

  // Ask the server whether a key is already connected (first time the panel opens).
  useEffect(() => {
    if (!open || status !== 'checking') return;
    let cancelled = false;
    fetch('/chat-api/status', { cache: 'no-store' })
      .then((r) => r.json())
      .then((d) => {
        if (!cancelled) setStatus(d.connected ? 'ready' : 'needs_key');
      })
      .catch(() => {
        if (!cancelled) setStatus('needs_key');
      });
    return () => {
      cancelled = true;
    };
  }, [open, status]);

  useEffect(() => {
    if (!open) return;
    endRef.current?.scrollIntoView({ block: 'end' });
    if (status === 'ready' && !busy) inputRef.current?.focus();
  }, [open, status, messages, busy, stage]);

  async function connect(e) {
    e.preventDefault();
    if (keyBusy) return;
    setKeyBusy(true);
    setKeyError('');
    try {
      const res = await fetch('/chat-api/key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: keyInput.trim() }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setKeyError(data.error || 'Could not connect. Please try again.');
        return;
      }
      setKeyInput('');
      setStatus('ready');
    } catch {
      setKeyError('Could not reach the server. Please try again.');
    } finally {
      setKeyBusy(false);
    }
  }

  async function disconnect() {
    try {
      await fetch('/chat-api/key', { method: 'DELETE' });
    } catch {}
    setStatus('needs_key');
    setKeyError('');
  }

  /** Replace the last message (the bot placeholder) using fn(previous). */
  function patchLast(fn) {
    setMessages((m) => (m.length ? [...m.slice(0, -1), fn(m[m.length - 1])] : m));
  }

  async function send(raw) {
    const text = raw.trim();
    if (!text || busy) return;

    const history = messages
      .filter((m) => !m.pending && m.text)
      .slice(-8)
      .map((m) => ({ role: m.role, text: m.text }));

    setMessages((m) => [...m, { role: 'user', text }, { role: 'bot', text: '', jobs: [], pending: true }]);
    setInput('');
    setStage('planning');
    setBusy(true);

    let finished = false;
    let keyProblem = null;

    try {
      const res = await fetch('/chat-api/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, history, last_search: lastSearch }),
      });

      const isStream = (res.headers.get('content-type') || '').includes('text/event-stream');

      if (!res.ok || !res.body || !isStream) {
        const data = await res.json().catch(() => null);
        finished = true;

        if (res.status === 401 && (data?.code === 'key_required' || data?.code === 'invalid_key')) {
          keyProblem = data.reply || 'Please connect your Mistral API key.';
        } else {
          patchLast(() => ({
            role: 'bot',
            text: data?.reply || 'Sorry, something went wrong. Please try again.',
            jobs: [],
          }));
        }
      } else {
        await readEvents(res, (event, data) => {
          if (event === 'status') {
            setStage(data.stage || '');
          } else if (event === 'jobs') {
            patchLast((m) => ({ ...m, jobs: data.jobs || [], total: data.total || 0 }));
          } else if (event === 'token') {
            patchLast((m) => ({ ...m, text: (m.text || '') + (data.t || '') }));
          } else if (event === 'done') {
            finished = true;
            setLastSearch(data.last_search || null);
            patchLast(() => ({
              role: 'bot',
              text: data.reply || '',
              jobs: data.jobs || [],
              total: data.total || 0,
              searchUrl: data.search_url,
              followUps: data.follow_ups || [],
              mode: data.mode,
              reranked: Boolean(data.reranked),
            }));
          } else if (event === 'error') {
            finished = true;
            if (data.code === 'invalid_key' || data.code === 'key_required') {
              keyProblem = data.reply || 'Please connect your Mistral API key.';
            } else {
              patchLast(() => ({
                role: 'bot',
                text: data.reply || 'Sorry, something went wrong. Please try again.',
                jobs: [],
              }));
            }
          }
        });
      }
    } catch {
      // network error or the stream was cut: handled below
    } finally {
      if (keyProblem) {
        setMessages((m) => m.slice(0, -2));
        setInput(text);
        setKeyError(keyProblem);
        setStatus('needs_key');
      } else if (!finished) {
        patchLast((m) =>
          m.text || m.jobs?.length
            ? { ...m, pending: false }
            : { role: 'bot', text: 'Sorry, I could not reach the search service. Please try again in a moment.', jobs: [] }
        );
      }
      setStage('');
      setBusy(false);
    }
  }

  function reset() {
    setMessages([WELCOME]);
    setLastSearch(null);
    try {
      sessionStorage.removeItem(STORAGE_KEY);
    } catch {}
  }

  const onlyWelcome = messages.length === 1;
  const lastIndex = messages.length - 1;

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
              <span>Powered by Mistral AI</span>
            </div>
            {status === 'ready' && (
              <>
                <button type="button" className="cb-icon" onClick={reset} title="Start a new chat">New</button>
                <button type="button" className="cb-icon" onClick={disconnect} title="Remove your API key from this browser">
                  Disconnect
                </button>
              </>
            )}
            <button type="button" className="cb-icon" onClick={() => setOpen(false)} aria-label="Close chat">
              <CloseIcon />
            </button>
          </header>

          {status === 'checking' && (
            <div className="cb-body"><p className="cb-note">Loading...</p></div>
          )}

          {status === 'needs_key' && (
            <div className="cb-body">
              <form className="cb-connect" onSubmit={connect}>
                <h3>Connect your Mistral AI key</h3>
                <p>
                  The assistant uses Mistral AI to understand your request. Paste your own API key to continue.
                  It is encrypted in a secure cookie, never saved in our database, and you can disconnect at any time.
                </p>
                {keyError && <p className="cb-error" role="alert">{keyError}</p>}
                <label htmlFor="mistral-key" className="sr">Mistral API key</label>
                <input
                  id="mistral-key"
                  type="password"
                  autoComplete="off"
                  spellCheck={false}
                  placeholder="Paste your Mistral API key"
                  value={keyInput}
                  onChange={(e) => setKeyInput(e.target.value)}
                />
                <button type="submit" disabled={keyBusy || keyInput.trim().length < 16}>
                  {keyBusy ? 'Checking your key...' : 'Connect and continue'}
                </button>
                <a href="https://console.mistral.ai/api-keys" target="_blank" rel="noopener noreferrer">
                  Get an API key from Mistral →
                </a>
              </form>
            </div>
          )}

          {status === 'ready' && (
            <>
              <div className="cb-body" role="log" aria-live="polite" aria-relevant="additions">
                {messages.map((m, i) => {
                  const waiting = m.pending && !m.text && !m.jobs?.length;

                  return (
                    <div key={i} className={m.role === 'user' ? 'cb-row user' : 'cb-row'}>
                      <div
                        className={
                          m.role === 'user' ? 'cb-bubble user' : waiting ? 'cb-bubble cb-typing' : 'cb-bubble'
                        }
                        aria-label={waiting ? 'The assistant is working' : undefined}
                      >
                        {waiting ? (
                          <>
                            <span /><span /><span />
                          </>
                        ) : (
                          <>
                            {(m.text || '').split('\n').map((line, k) => (
                              <p key={k}>{line}</p>
                            ))}

                            {m.jobs?.length > 0 && (
                              <ul className="cb-jobs">
                                {m.jobs.map((j) => {
                                  const href = safeUrl(j.url);
                                  const inner = (
                                    <>
                                      <span className="cb-job-title">{j.title}</span>
                                      <span className="cb-job-meta">
                                        {j.company}
                                        {j.location ? ` · ${j.location}` : ''}
                                      </span>
                                      {j.why && <span className="cb-why">{j.why}</span>}
                                      <span className="cb-job-foot">
                                        <span className="cb-job-tag">{j.source_label}</span>
                                        {j.match != null && <span className="cb-match">{j.match}% match</span>}
                                      </span>
                                    </>
                                  );
                                  return (
                                    <li key={j.id}>
                                      {href ? (
                                        <a className="cb-job" href={href} target="_blank" rel="nofollow noopener noreferrer">{inner}</a>
                                      ) : (
                                        <span className="cb-job">{inner}</span>
                                      )}
                                    </li>
                                  );
                                })}
                              </ul>
                            )}

                            {m.mode === 'keyword' && m.jobs?.length > 0 && (
                              <p className="cb-note">AI index unavailable, so I used keyword search.</p>
                            )}

                            {m.searchUrl && m.jobs?.length > 0 && !m.pending && (
                              <Link className="cb-more" href={m.searchUrl} prefetch={false} onClick={() => setOpen(false)}>
                                Open full search →
                              </Link>
                            )}
                          </>
                        )}
                      </div>
                    </div>
                  );
                })}

                {busy && stage && STAGES[stage] && <p className="cb-note cb-stage">{STAGES[stage]}</p>}

                {!busy && onlyWelcome && (
                  <ul className="cb-suggest" aria-label="Suggestions">
                    {SUGGESTIONS.map((s) => (
                      <li key={s}><button type="button" onClick={() => send(s)}>{s}</button></li>
                    ))}
                  </ul>
                )}

                {!busy && messages[lastIndex]?.followUps?.length > 0 && (
                  <ul className="cb-suggest" aria-label="Follow-up suggestions">
                    {messages[lastIndex].followUps.map((s) => (
                      <li key={s}><button type="button" onClick={() => send(s)}>{s}</button></li>
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
                  placeholder="Describe the job you want..."
                  aria-label="Your message"
                  maxLength={500}
                  autoComplete="off"
                  enterKeyHint="send"
                />
                <button type="submit" disabled={busy || !input.trim()} aria-label="Send message">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M5 12h14M13 6l6 6-6 6" />
                  </svg>
                </button>
              </form>
            </>
          )}
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
