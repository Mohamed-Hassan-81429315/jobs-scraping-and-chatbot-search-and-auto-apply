// Browser-only helpers for a conversation a guest has not saved yet.
// sessionStorage survives the redirect to /login and back (same tab) and is gone when the tab closes.

const PENDING_KEY = 'hirelume_pending_chat';
const DISMISS_KEY = 'hirelume_save_prompt_dismissed';
const TTL_MS = 60 * 60 * 1000; // an abandoned "OK" is forgotten after an hour
const MAX_MESSAGES = 200;

function store() {
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

export function newClientId() {
  try {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
  } catch {}
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
}

/** Keep only what the API accepts, in the order it was sent. */
function clean(messages) {
  return (messages || [])
    .filter((m) => m && (m.role === 'user' || m.role === 'assistant') && typeof m.content === 'string' && m.content.trim())
    .slice(0, MAX_MESSAGES)
    .map((m) => ({ role: m.role, content: m.content, ...(m.meta && typeof m.meta === 'object' ? { meta: m.meta } : {}) }));
}

export function savePending(messages, clientUuid) {
  const s = store();
  const list = clean(messages);
  if (!s || !list.length) return false;
  try {
    s.setItem(PENDING_KEY, JSON.stringify({ clientUuid: clientUuid || newClientId(), savedAt: Date.now(), messages: list }));
    return true;
  } catch {
    return false;
  }
}

export function readPending() {
  const s = store();
  if (!s) return null;
  try {
    const raw = s.getItem(PENDING_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw);
    if (!data || !Array.isArray(data.messages) || !data.messages.length) return null;
    if (Date.now() - Number(data.savedAt || 0) > TTL_MS) {
      s.removeItem(PENDING_KEY);
      return null;
    }
    return data;
  } catch {
    return null;
  }
}

export function clearPending() {
  try {
    store()?.removeItem(PENDING_KEY);
  } catch {}
}

export function isPromptDismissed() {
  try {
    return store()?.getItem(DISMISS_KEY) === '1';
  } catch {
    return false;
  }
}

export function dismissPrompt() {
  try {
    store()?.setItem(DISMISS_KEY, '1');
  } catch {}
}
