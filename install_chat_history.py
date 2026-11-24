#!/usr/bin/env python3
"""
Adds chat history to the Hirelume chatbot. Run from the project root:

    python3 install_chat_history.py
    cd jobs-backend && php artisan migrate

BACKEND   chat_conversations + chat_messages tables, ChatController, routes/chat.php
          (every query is scoped to the signed-in user, so people only see their own chats)
          Register no longer issues a token: the user must log in after registering.
FRONTEND  server actions, history sidebar, guest "save this conversation?" prompt (OK / No),
          importer that saves the guest conversation in order right after login,
          register -> login flow that keeps the page the user came from.

Every existing file that gets changed is backed up as <name>.prepatch first.
"""

import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(".")
BACK = ROOT / "jobs-backend"
FRONT = ROOT / "jobs-frontend"

if not (BACK / "artisan").exists() or not (FRONT / "app" / "page.js").exists():
    sys.exit("Run this from the project root (the folder that contains jobs-backend and jobs-frontend).")

FILES = {}

# =====================================================================
# BACKEND
# =====================================================================

FILES[BACK / "database/migrations/2026_11_22_000000_create_chat_tables.php"] = r'''<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('chat_conversations', function (Blueprint $table) {
            $table->id();
            $table->foreignId('user_id')->constrained()->cascadeOnDelete();
            // Generated in the browser. Makes "import my guest chat" idempotent.
            $table->uuid('client_uuid')->nullable();
            $table->string('title', 120)->default('New chat');
            $table->timestamps();

            $table->index(['user_id', 'updated_at']);
            $table->unique(['user_id', 'client_uuid']);
        });

        Schema::create('chat_messages', function (Blueprint $table) {
            $table->id();
            $table->foreignId('conversation_id')->constrained('chat_conversations')->cascadeOnDelete();
            // 1, 2, 3 ... the order the messages were sent. Never sort by timestamp.
            $table->unsignedInteger('position');
            $table->string('role', 16); // user | assistant
            $table->longText('content');
            $table->json('meta')->nullable(); // e.g. job cards the bot returned
            $table->timestamps();

            $table->unique(['conversation_id', 'position']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('chat_messages');
        Schema::dropIfExists('chat_conversations');
    }
};
'''

FILES[BACK / "app/Models/ChatConversation.php"] = r'''<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class ChatConversation extends Model
{
    protected $fillable = ['user_id', 'client_uuid', 'title'];

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    public function messages(): HasMany
    {
        return $this->hasMany(ChatMessage::class, 'conversation_id');
    }
}
'''

FILES[BACK / "app/Models/ChatMessage.php"] = r'''<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class ChatMessage extends Model
{
    protected $fillable = ['conversation_id', 'position', 'role', 'content', 'meta'];

    protected function casts(): array
    {
        return ['meta' => 'array'];
    }

    public function conversation(): BelongsTo
    {
        return $this->belongsTo(ChatConversation::class, 'conversation_id');
    }
}
'''

FILES[BACK / "app/Http/Controllers/ChatController.php"] = r'''<?php

namespace App\Http\Controllers;

use App\Models\ChatConversation;
use Illuminate\Database\UniqueConstraintViolationException;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

class ChatController extends Controller
{
    private const DEFAULT_TITLE = 'New chat';

    public function index(Request $request): JsonResponse
    {
        $rows = ChatConversation::where('user_id', $request->user()->id)
            ->orderByDesc('updated_at')
            ->orderByDesc('id')
            ->limit(200)
            ->get(['id', 'title', 'updated_at']);

        return response()->json(['conversations' => $rows]);
    }

    /**
     * Create a conversation. Optionally with its messages (used when a guest chat
     * is imported right after login). client_uuid makes a retry return the same chat.
     */
    public function store(Request $request): JsonResponse
    {
        $data = $request->validate($this->rules(true));
        $user = $request->user();
        $uuid = $data['client_uuid'] ?? null;

        if ($uuid && ($existing = $this->findByClientUuid($user->id, $uuid))) {
            return $this->respond($existing);
        }

        try {
            $conversation = DB::transaction(function () use ($data, $user, $uuid) {
                $messages = $data['messages'] ?? [];

                $conversation = ChatConversation::create([
                    'user_id' => $user->id,
                    'client_uuid' => $uuid,
                    'title' => $data['title'] ?? $this->titleFrom($messages),
                ]);

                $this->appendMessages($conversation, $messages);

                return $conversation;
            });
        } catch (UniqueConstraintViolationException $e) {
            // Two requests with the same client_uuid raced: return the winner.
            if ($uuid && ($existing = $this->findByClientUuid($user->id, $uuid))) {
                return $this->respond($existing);
            }
            throw $e;
        }

        return $this->respond($conversation, 201);
    }

    public function show(Request $request, int $id): JsonResponse
    {
        return $this->respond($this->owned($request, $id));
    }

    public function append(Request $request, int $id): JsonResponse
    {
        $conversation = $this->owned($request, $id);
        $data = $request->validate($this->rules(false));

        DB::transaction(function () use ($conversation, $data) {
            $locked = ChatConversation::whereKey($conversation->id)->lockForUpdate()->first();
            $this->appendMessages($locked, $data['messages']);
        });

        return response()->json(['ok' => true]);
    }

    public function update(Request $request, int $id): JsonResponse
    {
        $conversation = $this->owned($request, $id);
        $data = $request->validate(['title' => ['required', 'string', 'min:1', 'max:120']]);

        $conversation->update(['title' => trim($data['title'])]);

        return response()->json(['ok' => true]);
    }

    public function destroy(Request $request, int $id): JsonResponse
    {
        $this->owned($request, $id)->delete(); // messages cascade

        return response()->json(['ok' => true]);
    }

    // ------------------------------------------------------------------

    /** A conversation that belongs to the current user, or 404. Never leaks other users' chats. */
    private function owned(Request $request, int $id): ChatConversation
    {
        return ChatConversation::where('user_id', $request->user()->id)
            ->whereKey($id)
            ->firstOrFail();
    }

    private function findByClientUuid(int $userId, string $uuid): ?ChatConversation
    {
        return ChatConversation::where('user_id', $userId)->where('client_uuid', $uuid)->first();
    }

    private function rules(bool $creating): array
    {
        $meta = [
            'nullable',
            'array',
            function ($attribute, $value, $fail) {
                if (strlen((string) json_encode($value)) > 50000) {
                    $fail('Message metadata is too large.');
                }
            },
        ];

        return [
            ...($creating
                ? ['client_uuid' => ['nullable', 'uuid'], 'title' => ['nullable', 'string', 'max:120']]
                : []),
            'messages' => $creating ? ['nullable', 'array', 'max:200'] : ['required', 'array', 'min:1', 'max:50'],
            'messages.*.role' => ['required', 'in:user,assistant'],
            'messages.*.content' => ['required', 'string', 'max:20000'],
            'messages.*.meta' => $meta,
        ];
    }

    /** Append in order: position continues from the last stored message. */
    private function appendMessages(ChatConversation $conversation, array $messages): void
    {
        if (!$messages) {
            return;
        }

        $position = (int) $conversation->messages()->max('position');

        foreach ($messages as $m) {
            $position++;
            $conversation->messages()->create([
                'position' => $position,
                'role' => $m['role'],
                'content' => $m['content'],
                'meta' => $m['meta'] ?? null,
            ]);
        }

        if ($conversation->title === self::DEFAULT_TITLE) {
            $conversation->title = $this->titleFrom($messages);
        }
        $conversation->updated_at = now();
        $conversation->save();
    }

    private function titleFrom(array $messages): string
    {
        foreach ($messages as $m) {
            if (($m['role'] ?? '') === 'user') {
                $title = Str::limit(trim((string) preg_replace('/\s+/u', ' ', $m['content'])), 60, '…');
                if ($title !== '') {
                    return $title;
                }
            }
        }

        return self::DEFAULT_TITLE;
    }

    private function respond(ChatConversation $conversation, int $status = 200): JsonResponse
    {
        $conversation->load(['messages' => fn ($q) => $q->orderBy('position')]);

        return response()->json([
            'conversation' => [
                'id' => $conversation->id,
                'title' => $conversation->title,
                'updated_at' => $conversation->updated_at?->toIso8601String(),
                'messages' => $conversation->messages->map(fn ($m) => [
                    'id' => $m->id,
                    'role' => $m->role,
                    'content' => $m->content,
                    'meta' => $m->meta,
                    'created_at' => $m->created_at?->toIso8601String(),
                ])->values(),
            ],
        ], $status);
    }
}
'''

FILES[BACK / "routes/chat.php"] = r'''<?php

use App\Http\Controllers\ChatController;
use Illuminate\Support\Facades\Route;

// Loaded from routes/api.php, so these are /api/chat/...
Route::middleware(['auth:sanctum', 'throttle:120,1'])->prefix('chat')->group(function () {
    Route::get('/conversations', [ChatController::class, 'index']);
    Route::post('/conversations', [ChatController::class, 'store']);
    Route::get('/conversations/{id}', [ChatController::class, 'show'])->whereNumber('id');
    Route::post('/conversations/{id}/messages', [ChatController::class, 'append'])->whereNumber('id');
    Route::patch('/conversations/{id}', [ChatController::class, 'update'])->whereNumber('id');
    Route::delete('/conversations/{id}', [ChatController::class, 'destroy'])->whereNumber('id');
});
'''

# =====================================================================
# FRONTEND: shared config + server actions
# =====================================================================

FILES[FRONT / "lib/chatConfig.js"] = r'''// Where the chatbot lives and which query param selects a saved conversation.
// If the chatbot is not on the home page, change CHAT_PATH here (e.g. '/chat').
export const CHAT_PATH = '/';
export const CHAT_PARAM = 'chat';

export const chatHref = (id) => (id ? `${CHAT_PATH}?${CHAT_PARAM}=${id}` : CHAT_PATH);
'''

FILES[FRONT / "app/chat/actions.js"] = r'''"use server";

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
'''

# =====================================================================
# FRONTEND: guest save prompt (OK / No) + import after login
# =====================================================================

FILES[FRONT / "components/chat/guestChat.js"] = r'''// Browser-only helpers for a conversation a guest has not saved yet.
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
'''

FILES[FRONT / "components/chat/useGuestSavePrompt.js"] = r'''"use client";

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { dismissPrompt, isPromptDismissed, savePending } from './guestChat';

/**
 * Drives the "save this conversation?" prompt for guests.
 *  - shown once the bot has answered (and is not mid-stream), only when logged out
 *  - accept(): stash the conversation, send the user to /login, come back to this page
 *  - decline(): hide it and do nothing else; the user stays a guest
 */
export function useGuestSavePrompt({ loggedIn, messages, busy = false, clientUuid }) {
  const router = useRouter();
  const [dismissed, setDismissed] = useState(true); // true until mounted: no flash, no hydration mismatch

  useEffect(() => {
    setDismissed(isPromptDismissed());
  }, []);

  const hasReply = (messages || []).some((m) => m.role === 'assistant' && m.content);
  const visible = !loggedIn && hasReply && !busy && !dismissed;

  const accept = useCallback(() => {
    savePending(messages, clientUuid);
    const next = window.location.pathname + window.location.search;
    router.push(`/login?next=${encodeURIComponent(next)}`);
  }, [messages, clientUuid, router]);

  const decline = useCallback(() => {
    dismissPrompt();
    setDismissed(true);
  }, []);

  return { visible, accept, decline };
}
'''

FILES[FRONT / "components/chat/SaveChatPrompt.js"] = r'''"use client";

export default function SaveChatPrompt({ visible, onAccept, onDecline }) {
  if (!visible) return null;

  return (
    <div className="save-prompt" role="dialog" aria-live="polite" aria-label="Save this conversation">
      <p>
        Want to save this conversation? Log in now, and after you log in it will be saved for future use.
      </p>
      <div className="save-prompt-actions">
        <button type="button" className="btn-solid" onClick={onAccept}>OK</button>
        <button type="button" className="btn-ghost" onClick={onDecline}>No</button>
      </div>
    </div>
  );
}
'''

FILES[FRONT / "components/chat/PendingChatImporter.js"] = r'''"use client";

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { importGuestChat } from '../../app/chat/actions';
import { chatHref } from '../../lib/chatConfig';
import { clearPending, readPending } from './guestChat';

/** Mounted only for logged-in users. If a guest chat is waiting, save it, then open it. */
export default function PendingChatImporter() {
  const router = useRouter();
  const ran = useRef(false);
  const [note, setNote] = useState('');

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;

    const pending = readPending();
    if (!pending) return;

    (async () => {
      const res = await importGuestChat(pending);

      if (res?.ok && res.id) {
        clearPending();
        setNote('Your conversation was saved to your history.');
        router.replace(chatHref(res.id));
        router.refresh();
        setTimeout(() => setNote(''), 4000);
      } else if (res?.status === 422) {
        clearPending(); // invalid data will never succeed; do not retry forever
      } else if (res?.status !== 401) {
        setNote('We could not save your conversation. It will be retried on your next visit.');
        setTimeout(() => setNote(''), 6000);
      }
    })();
  }, [router]);

  if (!note) return null;
  return <div className="save-toast" role="status">{note}</div>;
}
'''

FILES[FRONT / "components/chat/ChatBootstrap.js"] = r'''import { getUser } from '../../lib/auth';
import PendingChatImporter from './PendingChatImporter';

/** Put once in the root layout. Renders nothing for guests. */
export default async function ChatBootstrap() {
  const user = await getUser();
  if (!user) return null;
  return <PendingChatImporter />;
}
'''

# =====================================================================
# FRONTEND: history sidebar
# =====================================================================

FILES[FRONT / "components/chat/ChatHistorySidebar.js"] = r'''import { getUser } from '../../lib/auth';
import { listConversations } from '../../app/chat/actions';
import ChatHistoryList from './ChatHistoryList';

/** Server component: only ever lists the signed-in user's chats. Renders nothing for guests. */
export default async function ChatHistorySidebar({ activeId = null }) {
  const user = await getUser();
  if (!user) return null;

  const items = await listConversations();
  return <ChatHistoryList items={items} activeId={activeId ? String(activeId) : null} />;
}
'''

FILES[FRONT / "components/chat/ChatHistoryList.js"] = r'''"use client";

import Link from 'next/link';
import { useEffect, useMemo, useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { deleteConversation } from '../../app/chat/actions';
import { CHAT_PATH, chatHref } from '../../lib/chatConfig';

const day = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();

function bucket(iso) {
  const days = Math.round((day(new Date()) - day(new Date(iso))) / 86400000);
  if (days <= 0) return 'Today';
  if (days === 1) return 'Yesterday';
  if (days <= 7) return 'Previous 7 days';
  return 'Older';
}

const ORDER = ['Today', 'Yesterday', 'Previous 7 days', 'Older'];

export default function ChatHistoryList({ items, activeId }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  // Group by the browser's local date, after mount (the server's timezone may differ).
  const groups = useMemo(() => {
    if (!mounted) return [['Recent', items]];
    const map = new Map();
    for (const it of items) {
      const key = bucket(it.updated_at);
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(it);
    }
    return ORDER.filter((k) => map.has(k)).map((k) => [k, map.get(k)]);
  }, [items, mounted]);

  function remove(id) {
    if (!window.confirm('Delete this conversation?')) return;
    start(async () => {
      const res = await deleteConversation(id);
      if (res?.ok) {
        if (String(id) === activeId) router.replace(CHAT_PATH);
        router.refresh();
      }
    });
  }

  return (
    <aside className="chat-history" aria-label="Chat history">
      <button type="button" className="btn-solid chat-new" onClick={() => router.push(`${CHAT_PATH}?new=${Date.now()}`)}>
        + New chat
      </button>

      {items.length === 0 && <p className="chat-empty">Your saved conversations will appear here.</p>}

      {groups.map(([label, list]) => (
        <section key={label}>
          <h3>{label}</h3>
          <ul>
            {list.map((c) => (
              <li key={c.id} className={String(c.id) === activeId ? 'active' : undefined}>
                <Link href={chatHref(c.id)} prefetch={false} title={c.title}>{c.title}</Link>
                <button type="button" onClick={() => remove(c.id)} disabled={pending} aria-label={`Delete ${c.title}`}>
                  &times;
                </button>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </aside>
  );
}
'''

# =====================================================================
# FRONTEND: register -> login (never auto-login), keeping the page you came from
# =====================================================================

FILES[FRONT / "app/login/page.js"] = r'''import Link from 'next/link';
import { redirect } from 'next/navigation';
import { getUser } from '../../lib/auth';
import AuthShell from '../../components/auth/AuthShell';
import LoginForm from '../../components/auth/LoginForm';

export const metadata = {
  title: 'Log in',
  description: 'Log in to your account.',
  robots: { index: false, follow: false },
  alternates: { canonical: '/login' },
};

function safeNext(value) {
  const v = typeof value === 'string' ? value : '/';
  return v.startsWith('/') && !v.startsWith('//') && !v.includes('\\') ? v : '/';
}

export default async function LoginPage({ searchParams }) {
  if (await getUser()) redirect('/');

  const sp = await searchParams;
  const next = safeNext(sp?.next);
  const registered = sp?.registered === '1';

  return (
    <AuthShell
      title={registered ? 'Account created' : 'Welcome back'}
      lead={registered ? 'Your account is ready. Log in to continue.' : 'Log in to continue.'}
      footer={
        <>
          New here?{' '}
          <Link href={`/register?next=${encodeURIComponent(next)}`} prefetch={false}>Create an account</Link>
        </>
      }
    >
      <LoginForm next={next} />
    </AuthShell>
  );
}
'''

FILES[FRONT / "app/register/page.js"] = r'''import Link from 'next/link';
import { redirect } from 'next/navigation';
import { getUser } from '../../lib/auth';
import AuthShell from '../../components/auth/AuthShell';
import RegisterForm from '../../components/auth/RegisterForm';

export const metadata = {
  title: 'Create your account',
  description: 'Create a free account.',
  robots: { index: false, follow: false },
  alternates: { canonical: '/register' },
};

function safeNext(value) {
  const v = typeof value === 'string' ? value : '/';
  return v.startsWith('/') && !v.startsWith('//') && !v.includes('\\') ? v : '/';
}

export default async function RegisterPage({ searchParams }) {
  if (await getUser()) redirect('/');

  const sp = await searchParams;
  const next = safeNext(sp?.next);

  return (
    <AuthShell
      title="Create your account"
      lead="It only takes a minute. You will log in right after."
      footer={
        <>
          Already have an account?{' '}
          <Link href={`/login?next=${encodeURIComponent(next)}`} prefetch={false}>Log in</Link>
        </>
      }
    >
      <RegisterForm next={next} />
    </AuthShell>
  );
}
'''

FILES[FRONT / "components/auth/RegisterForm.js"] = r'''"use client";

import { useActionState } from 'react';
import { registerAction } from '../../app/auth/actions';
import Field from './Field';
import PasswordField from './PasswordField';
import SubmitButton from './SubmitButton';

const INITIAL = { errors: {}, error: '', success: '', values: {} };

export default function RegisterForm({ next = '/' }) {
  const [state, action] = useActionState(registerAction, INITIAL);

  return (
    <form action={action} className="auth-form">
      {state.error && <p className="alert" role="alert">{state.error}</p>}
      <input type="hidden" name="next" value={next} />

      <Field
        id="name"
        name="name"
        label="Full name"
        autoComplete="name"
        defaultValue={state.values.name}
        error={state.errors.name}
        maxLength={100}
        autoFocus
      />
      <Field
        id="email"
        name="email"
        type="email"
        label="Email"
        autoComplete="email"
        defaultValue={state.values.email}
        error={state.errors.email}
        maxLength={255}
      />
      <PasswordField
        id="password"
        name="password"
        label="Password"
        autoComplete="new-password"
        minLength={8}
        hint="At least 8 characters, with letters and numbers."
        error={state.errors.password}
      />
      <PasswordField
        id="password_confirmation"
        name="password_confirmation"
        label="Confirm password"
        autoComplete="new-password"
        minLength={8}
        error={state.errors.password_confirmation}
      />
      <SubmitButton pendingLabel="Creating account...">Create account</SubmitButton>
    </form>
  );
}
'''

# =====================================================================
# CSS
# =====================================================================

CSS_MARK = "/* chat history */"
CSS = r'''

/* chat history */
.save-prompt { position: fixed; left: 50%; bottom: 20px; transform: translateX(-50%); z-index: 60; width: min(520px, calc(100% - 32px)); padding: 16px 18px; border-radius: 18px; background: #0e1328; border: 1px solid var(--line); box-shadow: 0 30px 80px -20px rgba(0, 0, 0, .75); }
.save-prompt p { font-size: .92rem; line-height: 1.5; margin-bottom: 12px; }
.save-prompt-actions { display: flex; gap: 8px; justify-content: flex-end; }
.save-toast { position: fixed; right: 20px; bottom: 20px; z-index: 60; max-width: min(380px, calc(100% - 40px)); padding: 12px 16px; border-radius: 14px; font-size: .9rem; background: #0e1328; border: 1px solid rgba(94, 234, 212, .4); color: #99f6e4; }
.chat-history { display: flex; flex-direction: column; gap: 14px; width: 260px; max-width: 100%; padding: 14px; border-radius: 18px; background: var(--panel); border: 1px solid var(--line); }
.chat-history .chat-new { width: 100%; }
.chat-history h3 { font-size: .72rem; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); margin: 0 0 6px 4px; }
.chat-history ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 2px; }
.chat-history li { display: flex; align-items: center; border-radius: 10px; }
.chat-history li:hover, .chat-history li.active { background: rgba(255, 255, 255, .07); }
.chat-history li a { flex: 1; min-width: 0; padding: 8px 10px; font-size: .9rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text); }
.chat-history li button { flex: none; width: 28px; height: 28px; margin-right: 4px; border: 0; border-radius: 8px; background: none; color: var(--muted); font-size: 1.1rem; cursor: pointer; opacity: 0; }
.chat-history li:hover button, .chat-history li button:focus-visible { opacity: 1; }
.chat-history li button:hover { color: #fca5a5; }
.chat-empty { font-size: .85rem; color: var(--muted); padding: 0 4px; }
'''

# =====================================================================
# Write new files / patch existing ones
# =====================================================================

def backup(path):
    bak = path.with_name(path.name + ".prepatch")
    if path.exists() and not bak.exists():
        shutil.copy2(path, bak)


MANUAL = []


def patch(path, fn, manual):
    """Apply fn(text)->text. If the expected code is not found, leave the file alone and say what to do."""
    if not path.exists():
        MANUAL.append(f"{path}: file not found. {manual}")
        return
    text = path.read_text(encoding="utf-8")
    new = fn(text)
    if new is None:
        MANUAL.append(f"{path}: expected code not found. {manual}")
        return
    if new != text:
        backup(path)
        path.write_text(new, encoding="utf-8")
        print(f"patched  {path}")
    else:
        print(f"already  {path}")


for path, content in FILES.items():
    backup(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"wrote    {path}")

# --- backend: load chat routes ----------------------------------------
REQUIRE = "require __DIR__ . '/chat.php';"


def patch_api(text):
    if "chat.php" in text:
        return text
    return text.rstrip() + "\n\n" + REQUIRE + "\n"


patch(BACK / "routes/api.php", patch_api, f"Add this line at the end of routes/api.php: {REQUIRE}")

# --- backend: register must not log the user in -----------------------
OLD_ISSUE = "return $this->issueToken($user, 201);"
NEW_ISSUE = (
    "// No token on purpose: the user must log in after registering.\n"
    "        return response()->json([\n"
    "            'user' => $this->present($user),\n"
    "            'message' => 'Account created. Please log in.',\n"
    "        ], 201);"
)


def patch_register_api(text):
    if NEW_ISSUE in text:
        return text
    if OLD_ISSUE not in text:
        return None
    return text.replace(OLD_ISSUE, NEW_ISSUE, 1)


patch(
    BACK / "app/Http/Controllers/AuthController.php",
    patch_register_api,
    "In register(), replace `return $this->issueToken($user, 201);` with a JSON response that has NO token.",
)

# --- frontend: register redirects to /login ---------------------------
REGISTER_RE = re.compile(
    r"(export async function registerAction.*?)await setSession\(res\.data\.token\);\s*redirect\(([\x27\"])/\2\);",
    re.DOTALL,
)
REGISTER_NEW = (
    "// The user must log in after registering: no session is created here.\n"
    "  redirect(`/login?registered=1&next=${encodeURIComponent(safeNext(formData.get('next')))}`);"
)


def patch_register_action(text):
    if "/login?registered=1" in text:
        return text
    if not REGISTER_RE.search(text):
        return None
    return REGISTER_RE.sub(lambda m: m.group(1) + REGISTER_NEW, text, count=1)


patch(
    FRONT / "app/auth/actions.js",
    patch_register_action,
    "In registerAction, delete `await setSession(...)` and redirect to "
    "`/login?registered=1&next=${encodeURIComponent(safeNext(formData.get('next')))}` instead of '/'.",
)

# --- frontend: mount the importer once in the layout ------------------
IMPORT_ANCHOR = "import UserMenu from '../components/UserMenu';"
IMPORT_NEW = IMPORT_ANCHOR + "\nimport ChatBootstrap from '../components/chat/ChatBootstrap';"
JSX_ANCHOR = "<UserMenu />"
JSX_NEW = "<UserMenu />\n          <ChatBootstrap />"


def patch_layout(text):
    if "ChatBootstrap" in text:
        return text
    if IMPORT_ANCHOR not in text or JSX_ANCHOR not in text:
        return None
    text = text.replace(IMPORT_ANCHOR, IMPORT_NEW, 1)
    return text.replace(JSX_ANCHOR, JSX_NEW, 1)


patch(
    FRONT / "app/layout.js",
    patch_layout,
    "Add `import ChatBootstrap from '../components/chat/ChatBootstrap';` and render <ChatBootstrap /> once inside <body>.",
)

# --- frontend: css ----------------------------------------------------
css_path = FRONT / "app/globals.css"
if css_path.exists():
    css_text = css_path.read_text(encoding="utf-8")
    if CSS_MARK not in css_text:
        backup(css_path)
        css_path.write_text(css_text.rstrip() + "\n" + CSS, encoding="utf-8")
        print(f"patched  {css_path}")
else:
    MANUAL.append(f"{css_path}: file not found. Paste the CSS block from this installer into your global stylesheet.")

print("\nDone.")
print("1) cd jobs-backend && php artisan migrate")
print("2) Wire the chatbot component (see the integration notes).")
if MANUAL:
    print("\nNeeds a manual step:")
    for m in MANUAL:
        print(" -", m)
