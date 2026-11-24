'use client';

import { useCallback, useEffect, useId, useRef, useState } from 'react';
import { greetingFor } from './greeting';
import './chat.css';

const SUGGESTIONS = ['Remote developer jobs', 'Marketing jobs', 'Data analyst', 'Part-time jobs'];
const EMOJIS = ['😀', '😊', '👍', '🙏', '🎉', '💼', '🚀', '👋', '😅', '🤔', '✅', '❤️'];
const MAX_LEN = 500;
const NAME_KEY = 'applyra_chat_name';
const CONSENT_KEY = 'applyra_chat_consent_closed';

const safeUrl = (u) => (typeof u === 'string' && /^https?:\/\//i.test(u) ? u : null);
const store = {
  get(k) { try { return window.localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { window.localStorage.setItem(k, v); } catch {} },
};

function Sparkle({ size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 2c.6 5.5 4.5 9.4 10 10-5.5.6-9.4 4.5-10 10-.6-5.5-4.5-9.4-10-10 5.5-.6 9.4-4.5 10-10z" fill="#FFE23A" />
    </svg>
  );
}

function Avatar({ size = 'sm', online = false }) {
  return (
    <span className={`ac__ava ac__ava--${size}`} aria-hidden="true">
      <Sparkle size={size === 'lg' ? 22 : 13} />
      {online && <i className="ac__online" />}
    </span>
  );
}

export default function ChatWidget() {
  const panelId = useId();
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [emojiOpen, setEmojiOpen] = useState(false);
  const [topicsOpen, setTopicsOpen] = useState(false);
  const [consentClosed, setConsentClosed] = useState(true); // true until we know (avoids a flash)
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [awaitingName, setAwaitingName] = useState(false);
  const [userName, setUserName] = useState('');
  const started = useRef(false);
  const launcher = useRef(null);
  const field = useRef(null);
  const endRef = useRef(null);

  useEffect(() => {
    setConsentClosed(store.get(CONSENT_KEY) === '1');
  }, []);

  // The greeting is built when the window first opens: visitor's clock + account (or remembered) name.
  const start = useCallback(async () => {
    if (started.current) return;
    started.current = true;
    let name = '';
    try {
      const ctrl = new AbortController();
      const t = setTimeout(() => ctrl.abort(), 2500);
      const res = await fetch('/api/chat/user', { signal: ctrl.signal, cache: 'no-store' });
      clearTimeout(t);
      if (res.ok) name = ((await res.json()).name || '').trim();
    } catch {}
    if (!name) name = (store.get(NAME_KEY) || '').trim();

    const greeting = greetingFor();
    setUserName(name);
    if (name) {
      setAwaitingName(false);
      setMessages([{ id: 'hello', role: 'bot', skip: true, text: `${greeting} ${name}! Which job are you looking for today?` }]);
    } else {
      setAwaitingName(true);
      setMessages([{ id: 'hello', role: 'bot', skip: true, text: `${greeting}. Welcome to Applyra. Please tell me your name so I can assist you better.` }]);
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    start();
    const t = setTimeout(() => field.current?.focus(), 60);
    return () => clearTimeout(t);
  }, [open, start]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end' });
  }, [messages, sending, open, topicsOpen]);

  const close = useCallback(() => {
    setOpen(false);
    setMenuOpen(false);
    setEmojiOpen(false);
    launcher.current?.focus();
  }, []);

  function clearChat() {
    setMenuOpen(false);
    started.current = false;
    setMessages([]);
    setTopicsOpen(false);
    start();
  }

  function resize(el) {
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 110)}px`;
  }

  function addEmoji(emoji) {
    const el = field.current;
    const s = el?.selectionStart ?? input.length;
    const e = el?.selectionEnd ?? input.length;
    const next = (input.slice(0, s) + emoji + input.slice(e)).slice(0, MAX_LEN);
    setInput(next);
    setEmojiOpen(false);
    setTimeout(() => {
      el?.focus();
      el?.setSelectionRange(s + emoji.length, s + emoji.length);
    }, 0);
  }

  const push = (m) => setMessages((list) => [...list, { id: `${m.role}${Date.now()}${Math.random()}`, ...m }]);

  async function send(raw) {
    const text = (raw ?? input).trim();
    if (!text || sending) return;
    setInput('');
    setTopicsOpen(false);
    setEmojiOpen(false);
    if (field.current) field.current.style.height = 'auto';
    // Conversation memory sent to the server: real chat turns only (onboarding turns are flagged skip).
    const history = messages
      .filter((m) => !m.skip && m.text)
      .slice(-8)
      .map((m) => ({ role: m.role === 'bot' ? 'assistant' : 'user', content: String(m.text).slice(0, 1000) }));
    push({ role: 'user', text, skip: awaitingName });

    // First reply of a guest is their name.
    if (awaitingName) {
      const name = text.replace(/[^\p{L}\p{N} '\-]/gu, '').trim().slice(0, 40);
      if (!name) {
        push({ role: 'bot', skip: true, text: 'Please type your name using letters, for example "Sara".' });
        return;
      }
      store.set(NAME_KEY, name);
      setUserName(name);
      setAwaitingName(false);
      push({ role: 'bot', skip: true, text: `Nice to meet you, ${name}. Which job are you looking for?` });
      return;
    }

    setSending(true);
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 45000); // the AI can take a while; do not hang forever
    try {
      const res = await fetch('/api/backend/chat', {
        method: 'POST',
        signal: ctrl.signal,
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ message: text, history, user_name: userName || undefined }),
      });
      const data = await res.json().catch(() => ({}));
      let reply;
      if (res.status === 429) reply = 'You are sending messages very fast. Wait a few seconds and try again.';
      else if (res.status === 422) reply = 'That message could not be sent. Keep it under 500 characters and try again.';
      else if (res.ok) reply = data.reply;
      else reply = 'Sorry, I could not reach the assistant. Try again in a moment.';
      push({ role: 'bot', text: reply || 'Sorry, I have no answer for that.', jobs: res.ok ? data.jobs : undefined });
    } catch (err) {
      push({
        role: 'bot',
        text: err?.name === 'AbortError' ? 'That took too long. Please try again.' : 'Network error. Check your connection and try again.',
      });
    } finally {
      clearTimeout(timer);
      setSending(false);
      field.current?.focus();
    }
  }

  function onKeyDown(e) {
    // Enter sends, Shift+Enter adds a new line (IME composition is left alone)
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      send();
    }
  }

  const showChips = (messages.length <= 1 && !awaitingName && !sending) || topicsOpen;

  return (
    <div className="ac" onKeyDown={(e) => e.key === 'Escape' && open && close()}>
      {open && (
        <section
          id={panelId}
          className={`ac__panel${expanded ? ' ac__panel--wide' : ''}`}
          role="dialog"
          aria-modal="false"
          aria-label="Applyra job assistant"
        >
          <div className="ac__bar">
            <button type="button" className="ac__round" onClick={() => setExpanded((v) => !v)} aria-label={expanded ? 'Make chat smaller' : 'Make chat larger'}>
              <svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true">
                {expanded ? (
                  <path d="M9 3v6H3M15 21v-6h6M3 9l6-6M21 15l-6 6" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
                ) : (
                  <path d="M4 10V4h6M20 14v6h-6M4 4l6 6M20 20l-6-6" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
                )}
              </svg>
            </button>
            <div className="ac__bar-right">
              <div className="ac__menuwrap">
                <button type="button" className="ac__round" onClick={() => setMenuOpen((v) => !v)} aria-label="More options" aria-expanded={menuOpen} aria-haspopup="menu">
                  <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
                    <circle cx="5" cy="12" r="2" fill="currentColor" /><circle cx="12" cy="12" r="2" fill="currentColor" /><circle cx="19" cy="12" r="2" fill="currentColor" />
                  </svg>
                </button>
                {menuOpen && (
                  <div className="ac__menu" role="menu">
                    <button type="button" role="menuitem" onClick={clearChat}>Start a new conversation</button>
                    <button type="button" role="menuitem" onClick={close}>Close chat</button>
                  </div>
                )}
              </div>
              <button type="button" className="ac__round" onClick={close} aria-label="Close chat">
                <svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" />
                </svg>
              </button>
            </div>
          </div>

          <div className="ac__agent">
            <Avatar size="lg" online />
            <div>
              <strong>Applyra Assistant</strong>
              <span>AI job assistant</span>
            </div>
          </div>

          <div className="ac__log" role="log" aria-live="polite" aria-relevant="additions">
            {messages.map((m) => (
              <div key={m.id} className={`ac__msg ac__msg--${m.role}`}>
                {m.role === 'bot' ? (
                  <div className="ac__botrow">
                    <Avatar />
                    <div className="ac__text">{m.text}</div>
                  </div>
                ) : (
                  <div className="ac__bubble">{m.text}</div>
                )}
                {m.jobs?.length > 0 && (
                  <ul className="ac__jobs">
                    {m.jobs.map((j) => (
                      <li key={j.id ?? j.title}>
                        {safeUrl(j.url) ? (
                          <a href={safeUrl(j.url)} target="_blank" rel="noopener noreferrer">{j.title}</a>
                        ) : (
                          <strong>{j.title}</strong>
                        )}
                        <span>{[j.company, j.location].filter(Boolean).join(' · ')}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}

            {showChips && (
              <div className="ac__chips">
                {SUGGESTIONS.map((s) => (
                  <button key={s} type="button" onClick={() => send(s)}>{s}</button>
                ))}
              </div>
            )}

            {sending && (
              <div className="ac__msg ac__msg--bot" aria-label="Assistant is typing">
                <div className="ac__botrow">
                  <Avatar />
                  <div className="ac__typing"><i /><i /><i /></div>
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>

          {!consentClosed && (
            <div className="ac__consent" role="note">
              <p>By chatting here, you agree that your messages are processed to search job listings.</p>
              <button
                type="button"
                className="ac__consent-x"
                aria-label="Dismiss notice"
                onClick={() => { setConsentClosed(true); store.set(CONSENT_KEY, '1'); }}
              >
                <svg width="10" height="10" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="3.2" strokeLinecap="round" /></svg>
              </button>
            </div>
          )}

          <form className="ac__form" onSubmit={(e) => { e.preventDefault(); send(); }}>
            {emojiOpen && (
              <div className="ac__emoji" role="group" aria-label="Emoji">
                {EMOJIS.map((em) => (
                  <button key={em} type="button" onClick={() => addEmoji(em)} aria-label={`Insert ${em}`}>{em}</button>
                ))}
              </div>
            )}
            <div className="ac__pill">
              <button
                type="button"
                className="ac__icon ac__icon--dark"
                onClick={() => { setTopicsOpen((v) => !v); setEmojiOpen(false); }}
                aria-label="Show suggested searches"
                aria-pressed={topicsOpen}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2.8" strokeLinecap="round" /></svg>
              </button>
              <label htmlFor={`${panelId}-in`} className="ac__sr">Message</label>
              <textarea
                id={`${panelId}-in`}
                ref={field}
                rows={1}
                value={input}
                maxLength={MAX_LEN}
                placeholder={awaitingName ? 'Type your name…' : 'Write a message…'}
                onChange={(e) => { setInput(e.target.value); resize(e.target); }}
                onKeyDown={onKeyDown}
              />
              <button
                type="button"
                className="ac__icon ac__icon--ghost"
                onClick={() => { setEmojiOpen((v) => !v); setTopicsOpen(false); }}
                aria-label="Add emoji"
                aria-pressed={emojiOpen}
              >
                <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true">
                  <circle cx="12" cy="12" r="9.5" fill="none" stroke="currentColor" strokeWidth="2" />
                  <circle cx="9" cy="10" r="1.2" fill="currentColor" /><circle cx="15" cy="10" r="1.2" fill="currentColor" />
                  <path d="M8 14.2c1 1.5 2.4 2.2 4 2.2s3-.7 4-2.2" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
              </button>
              <button type="submit" className="ac__send" disabled={!input.trim() || sending} aria-label="Send message">
                <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 19V5M5 12l7-7 7 7" fill="none" stroke="currentColor" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
              </button>
            </div>
            {input.length > MAX_LEN - 80 && <span className="ac__count">{input.length}/{MAX_LEN}</span>}
          </form>
        </section>
      )}

      <button
        ref={launcher}
        type="button"
        className="ac__launcher"
        onClick={() => (open ? close() : setOpen(true))}
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        aria-label={open ? 'Close chat' : 'Open job assistant chat'}
      >
        <svg width="26" height="26" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M4 4h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9l-5 4v-4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z" fill="currentColor" />
          <circle cx="8.5" cy="11" r="1.3" fill="#fff" /><circle cx="12.5" cy="11" r="1.3" fill="#fff" /><circle cx="16.5" cy="11" r="1.3" fill="#fff" />
        </svg>
      </button>
    </div>
  );
}
