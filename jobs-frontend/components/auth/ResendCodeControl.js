"use client";

import { useActionState, useEffect, useState } from 'react';
import { resendOtpAction } from '../../app/auth/otp-actions';
import styles from './OtpSentDialog.module.css';

const INITIAL = { errors: {}, error: '', success: '', values: {} };
const RESEND_WAIT_MS = 60_000;

function formatCountdown(totalSeconds) {
  const minutes = Math.floor(totalSeconds / 60).toString().padStart(2, '0');
  const seconds = (totalSeconds % 60).toString().padStart(2, '0');
  return `${minutes}:${seconds}`;
}

export default function ResendCodeControl({ email, initialSentAt = 0, onResent, variant = 'page' }) {
  const [state, action, pending] = useActionState(resendOtpAction, INITIAL);
  const [now, setNow] = useState(0);
  const latestSentAt = Number(state.sentAt) || Number(initialSentAt) || 0;
  const deadline = latestSentAt > 0 ? latestSentAt + RESEND_WAIT_MS : 0;
  const remaining = deadline
    ? Math.max(0, Math.ceil((deadline - (now || deadline - RESEND_WAIT_MS)) / 1000))
    : 0;

  useEffect(() => {
    if (!state.sentAt) return;
    onResent?.(Number(state.sentAt));
  }, [state.sentAt, onResent]);

  useEffect(() => {
    if (!deadline) {
      return undefined;
    }

    let timer;
    const tick = () => {
      const timestamp = Date.now();
      setNow(timestamp);
      if (timestamp < deadline) {
        timer = window.setTimeout(tick, Math.min(1000, deadline - timestamp));
      }
    };
    timer = window.setTimeout(tick, 0);
    return () => {
      window.clearTimeout(timer);
    };
  }, [deadline]);

  const isDialog = variant === 'dialog';
  const disabled = pending || remaining > 0;

  return (
    <div className={`${styles.resend} ${isDialog ? styles.resendDialog : ''}`}>
      <form action={action}>
        <input type="hidden" name="email" value={email} />
        <button type="submit" className={styles.resendButton} disabled={disabled}>
          {pending ? (
            <><span className={styles.spinner} aria-hidden="true" /> Sending code…</>
          ) : 'Resend Code'}
        </button>
      </form>
      {remaining > 0 ? (
        <p className={styles.cooldown} role="status" aria-live="polite">
          You can request another code in <strong>{formatCountdown(remaining)}</strong>.
        </p>
      ) : null}
      {state.error ? <p className={styles.error} role="alert">{state.error}</p> : null}
      {state.success === 'resend-requested' ? (
        <p className={styles.resendSuccess} role="status" aria-live="polite">
          If an account exists for this email, a new code is on its way.
        </p>
      ) : null}
    </div>
  );
}
