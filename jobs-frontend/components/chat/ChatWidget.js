"use client";

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
