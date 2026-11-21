export default function Field({
  id,
  name,
  label,
  type = 'text',
  autoComplete,
  defaultValue,
  error,
  hint,
  required = true,
  maxLength,
  autoFocus = false,
}) {
  const describedBy = error ? `${id}-err` : hint ? `${id}-hint` : undefined;

  return (
    <div className="fld">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        name={name}
        type={type}
        autoComplete={autoComplete}
        defaultValue={defaultValue}
        required={required}
        maxLength={maxLength}
        autoFocus={autoFocus}
        aria-invalid={error ? 'true' : undefined}
        aria-describedby={describedBy}
      />
      {error ? (
        <p className="err" id={`${id}-err`}>{error}</p>
      ) : hint ? (
        <p className="hint" id={`${id}-hint`}>{hint}</p>
      ) : null}
    </div>
  );
}
