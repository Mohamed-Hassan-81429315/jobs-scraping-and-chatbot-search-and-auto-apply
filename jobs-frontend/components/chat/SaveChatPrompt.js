"use client";

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
