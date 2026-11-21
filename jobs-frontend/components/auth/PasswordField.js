"use client";

import { useState } from 'react';

export default function PasswordField({ id, name, label, autoComplete, error, hint, minLength }) {
  const [shown, setShown] = useState(false);
  const describedBy = error ? `${id}-err` : hint ? `${id}-hint` : undefined;

  return (
    <div className="fld">
      <label htmlFor={id}>{label}</label>
      <div className="pw">
        <input
          id={id}
          name={name}
          type={shown ? 'text' : 'password'}
          autoComplete={autoComplete}
          required
          minLength={minLength}
          aria-invalid={error ? 'true' : undefined}
          aria-describedby={describedBy}
        />
        <button type="button" onClick={() => setShown(!shown)} aria-pressed={shown}>
          {shown ? 'Hide' : 'Show'}
          <span className="sr"> password</span>
        </button>
      </div>
      {error ? (
        <p className="err" id={`${id}-err`}>{error}</p>
      ) : hint ? (
        <p className="hint" id={`${id}-hint`}>{hint}</p>
      ) : null}
    </div>
  );
}
