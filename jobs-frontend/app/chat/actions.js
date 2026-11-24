"use server";

import { api, getToken } from '../../lib/auth';

const ID = /^\d+$/;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const MAX_MESSAGES = 200;
const MAX_CONTENT = 20000;

async function authed(path, opts = {}) {
  const token = await getToken();
  if (!token) return { ok: false, status: 401, data: null };
  return api(path, { ...opts, token });
}

function cleanMessages(list) {
  if (!Array.isArray(list)) return [];
  const out = [];
  for (const m of list.slice(0, MAX_MESSAGES)) {
    if (!m || (m.role !== 'user' && m.role !== 'assistant')) continue;
    const content = typeof m.content === 'string' ? m.content.trim().slice(0, MAX_CONTENT) : '';
    if (!content) continue;
    const item = { role: m.role, content };
    if (m.meta && typeof m.meta === 'object' && !Array.isArray(m.meta)) item.meta = m.meta;
    out.push(item);
  }
  return out;
}

/** Sidebar list for the signed-in user. Empty list when logged out. */
export async function listConversations() {
  const res = await authed('/chat/conversations');
  return res.ok ? res.data?.conversations ?? [] : [];
}

/** One conversation with its messages in order, or null (also null for someone else's chat). */
export async function loadConversation(id) {
  if (!ID.test(String(id ?? ''))) return null;
  const res = await authed(`/chat/conversations/${id}`);
  return res.ok ? res.data?.conversation ?? null : null;
}

/**
 * Persist one exchange for a logged-in user.
 * - no conversationId yet: creates the conversation and returns its id
 * - with conversationId: appends in order
 */
export async function saveTurn({ conversationId, clientUuid, messages }) {
  const clean = cleanMessages(messages);
  if (!clean.length) return { ok: false, status: 422, id: conversationId ?? null };

  if (conversationId) {
    if (!ID.test(String(conversationId))) return { ok: false, status: 422, id: null };
    const res = await authed(`/chat/conversations/${conversationId}/messages`, {
      method: 'POST',
      body: { messages: clean },
    });
    return { ok: res.ok, status: res.status, id: conversationId };
  }

  const res = await authed('/chat/conversations', {
    method: 'POST',
    body: { client_uuid: UUID.test(String(clientUuid ?? '')) ? clientUuid : undefined, messages: clean },
  });
  return { ok: res.ok, status: res.status, id: res.data?.conversation?.id ?? null };
}

/** Save a guest conversation right after login. Safe to retry (client_uuid dedupes). */
export async function importGuestChat(pending) {
  const messages = cleanMessages(pending?.messages);
  if (!messages.length) return { ok: false, status: 422, id: null };

  const clientUuid = String(pending?.clientUuid ?? '');
  const res = await authed('/chat/conversations', {
    method: 'POST',
    body: { client_uuid: UUID.test(clientUuid) ? clientUuid : undefined, messages },
  });
  return { ok: res.ok, status: res.status, id: res.data?.conversation?.id ?? null };
}

export async function renameConversation(id, title) {
  if (!ID.test(String(id ?? ''))) return { ok: false };
  const res = await authed(`/chat/conversations/${id}`, { method: 'PATCH', body: { title: String(title ?? '') } });
  return { ok: res.ok };
}

export async function deleteConversation(id) {
  if (!ID.test(String(id ?? ''))) return { ok: false };
  const res = await authed(`/chat/conversations/${id}`, { method: 'DELETE' });
  return { ok: res.ok };
}
