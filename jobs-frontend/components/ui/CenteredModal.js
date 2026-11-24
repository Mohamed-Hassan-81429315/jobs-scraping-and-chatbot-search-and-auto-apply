"use client";

import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';

/**
 * Puts any dialog in the exact middle of the screen.
 *
 * It renders into <body> through a portal, so a parent with transform / filter / overflow
 * can no longer push a "position: fixed" card off to the side.
 *
 * Props
 *   onClose          optional: called on Escape (and on backdrop click if closeOnBackdrop)
 *   closeOnBackdrop  default false (an OTP dialog should not vanish by accident)
 *   label            accessible name of the dialog
 */
export default function CenteredModal({ children, onClose, closeOnBackdrop = false, label = 'Dialog' }) {
  const [mounted, setMounted] = useState(false);

  // Lock page scroll while the dialog is open.
  useEffect(() => {
    setMounted(true);
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previous;
    };
  }, []);

  useEffect(() => {
    if (!onClose) return undefined;
    const onKey = (e) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  if (!mounted) return null;

  return createPortal(
    <div
      className="modal-backdrop"
      onMouseDown={(e) => closeOnBackdrop && e.target === e.currentTarget && onClose?.()}
    >
      <div className="modal-center" role="dialog" aria-modal="true" aria-label={label}>
        {children}
      </div>
    </div>,
    document.body
  );
}
