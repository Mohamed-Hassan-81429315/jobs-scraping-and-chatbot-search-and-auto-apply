"use client";

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
