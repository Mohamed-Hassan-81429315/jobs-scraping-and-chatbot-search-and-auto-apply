export function LogoMark({ size = 18 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="8 8 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="3.4"
      strokeLinecap="round"
      aria-hidden="true"
    >
      <path d="M12 11v18M28 11v18" />
      <circle cx="20" cy="20" r="4.6" />
      <path d="M13.5 20h1.9M24.6 20h1.9" />
    </svg>
  );
}
