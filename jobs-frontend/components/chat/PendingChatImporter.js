"use client";

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
