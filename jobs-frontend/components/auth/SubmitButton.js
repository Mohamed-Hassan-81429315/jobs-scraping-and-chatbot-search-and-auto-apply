"use client";

import { useFormStatus } from 'react-dom';

export default function SubmitButton({ children, pendingLabel }) {
  const { pending } = useFormStatus();

  return (
    <button type="submit" className="auth-submit" disabled={pending}>
      {pending ? pendingLabel : children}
    </button>
  );
}
