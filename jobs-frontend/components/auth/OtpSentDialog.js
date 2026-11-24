"use client";

import { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import ResendCodeControl from './ResendCodeControl';
import styles from './OtpSentDialog.module.css';

export default function OtpSentDialog({ email, sentAt }) {
  const router = useRouter();
  const dialogRef = useRef(null);
  const confirmRef = useRef(null);
  const latestSentAtRef = useRef(sentAt);
  const [dismissedSentAt, setDismissedSentAt] = useState(0);
  const isOpen = Boolean(email && sentAt && dismissedSentAt !== sentAt);

  useEffect(() => {
    latestSentAtRef.current = sentAt;
  }, [sentAt]);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return undefined;

    if (!isOpen) {
      if (dialog.open) dialog.close();
      return undefined;
    }

    if (!dialog.open) {
      dialog.showModal();
      confirmRef.current?.focus(); // the primary action, not the close button
    }

    // A modal <dialog> makes the page inert but the page can still scroll behind the backdrop.
    // Lock it, and keep the layout from jumping when the scrollbar disappears.
    const root = document.documentElement;
    const previousOverflow = root.style.overflow;
    const previousPadding = root.style.paddingRight;
    const scrollbar = window.innerWidth - root.clientWidth;
    root.style.overflow = 'hidden';
    if (scrollbar > 0) root.style.paddingRight = `${scrollbar}px`;

    return () => {
      root.style.overflow = previousOverflow;
      root.style.paddingRight = previousPadding;
    };
  }, [isOpen]);

  const handleResent = useCallback((timestamp) => {
    latestSentAtRef.current = timestamp;
  }, []);

  function continueToCodeEntry() {
    setDismissedSentAt(sentAt);
    const params = new URLSearchParams({ email, sentAt: String(latestSentAtRef.current || sentAt) });
    router.push(`/reset-password?${params.toString()}`);
  }

  if (!email || !sentAt) return null;

  return (
    <dialog
      ref={dialogRef}
      className={styles.dialog}
      aria-labelledby="otp-sent-title"
      aria-describedby="otp-sent-description"
      onClose={() => setDismissedSentAt(sentAt)}
      onClick={(event) => {
        if (event.target === dialogRef.current) setDismissedSentAt(sentAt);
      }}
    >
      <section className={styles.card}>
        <button
          type="button"
          className={styles.close}
          aria-label="Close confirmation"
          onClick={() => setDismissedSentAt(sentAt)}
        >
          <svg viewBox="0 0 20 20" aria-hidden="true"><path d="m5 5 10 10M15 5 5 15" /></svg>
        </button>

        <div className={styles.mailIcon} aria-hidden="true">
          <svg viewBox="0 0 48 48"><rect x="6" y="10" width="36" height="28" rx="6" /><path d="m8 14 16 12 16-12" /></svg>
        </div>

        <p className={styles.eyebrow}>Code requested</p>
        <h2 id="otp-sent-title" className={styles.title}>Check your email</h2>
        <div className={styles.notice}>
          <p className={styles.noticeLabel}>OTP code requested for</p>
          <p className={styles.email}>{email}</p>
        </div>
        <p id="otp-sent-description" className={styles.description}>
          If an Applyra account exists for this address, a verification code is on its way. Check your inbox and spam folder now. If you do not receive a code, use Resend Code below after the one-minute cooldown.
        </p>

        <ResendCodeControl
          email={email}
          initialSentAt={sentAt}
          onResent={handleResent}
          variant="dialog"
        />

        <button ref={confirmRef} type="button" className={styles.confirm} onClick={continueToCodeEntry}>
          OK, Received It
          <span aria-hidden="true">→</span>
        </button>
      </section>
    </dialog>
  );
}
