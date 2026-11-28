// One-tab hand-off for the password-reset email button.
// The email link always opens a NEW tab. That new tab (same site, same browser) tells the
// tab where the user asked for the code, and that original tab moves to the code screen and
// fills the code. Same-origin only (BroadcastChannel), so no other site can send or hear it.
const CHANNEL = 'applyra-otp-handoff';
export const HANDOFF_KEY = 'applyra-otp-handoff';

const open = () => {
  try { return typeof BroadcastChannel === 'undefined' ? null : new BroadcastChannel(CHANNEL); } catch { return null; }
};
const same = (a, b) => String(a || '').trim().toLowerCase() === String(b || '').trim().toLowerCase();

/** New tab: offer the code to an original tab. Resolves true if one accepted it. */
export function sendCode(email, code, timeoutMs = 900) {
  return new Promise((resolve) => {
    const ch = open();
    if (!ch) return resolve(false);
    const id = Math.random().toString(36).slice(2);
    const finish = (ok) => { clearTimeout(timer); ch.close(); resolve(ok); };
    const timer = setTimeout(() => finish(false), timeoutMs);
    ch.onmessage = (e) => { if (e.data?.type === 'ack' && e.data.id === id) finish(true); };
    ch.postMessage({ type: 'code', id, email, code });
  });
}

/** Original tab: accept a code for this email. Returns a function that stops listening. */
export function listenForCode(email, onCode) {
  const ch = open();
  if (!ch) return () => {};
  ch.onmessage = (e) => {
    const d = e.data;
    if (d?.type !== 'code' || !/^\d{6}$/.test(String(d.code)) || !same(d.email, email)) return;
    ch.postMessage({ type: 'ack', id: d.id });
    onCode(String(d.code));
  };
  return () => ch.close();
}

/** Original tab -> reset page (client-side navigation): hand the code over for 2 minutes. */
export function stashCode(email, code) {
  try { sessionStorage.setItem(HANDOFF_KEY, JSON.stringify({ email, code, at: Date.now() })); } catch {}
}
export function takeStashedCode(email) {
  try {
    const raw = sessionStorage.getItem(HANDOFF_KEY);
    if (!raw) return '';
    sessionStorage.removeItem(HANDOFF_KEY);
    const o = JSON.parse(raw);
    return same(o.email, email) && /^\d{6}$/.test(String(o.code)) && Date.now() - o.at < 120000 ? String(o.code) : '';
  } catch { return ''; }
}
