import Link from 'next/link';
import Image from 'next/image';

export function LogoMark({ size = 36 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" role="img" aria-label="Applyra logo" xmlns="http://www.w3.org/2000/svg">
      <rect width="40" height="40" rx="10" fill="#12263F" />
      <path d="M11.5 29.5 20 10.5l8.5 19" fill="none" stroke="#fff" strokeWidth="3.6" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="20" cy="25" r="3.1" fill="#2EE6A6" />
    </svg>
  );
}

export default function BrandLogo({ light = false, image = false }) {
  return (
    <Link href="/" className={`brand${light ? ' brand--light' : ''}`} aria-label="Applyra home">
      {image ? (
        <Image src="/applyra-logo.png" alt="" width={36} height={36} priority style={{ width: 36, height: 'auto' }} />
      ) : (
        <LogoMark />
      )}
      <span className="brand__word">Applyra</span>
    </Link>
  );
}
