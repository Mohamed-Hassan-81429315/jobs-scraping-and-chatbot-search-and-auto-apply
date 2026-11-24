"use client";

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
