import { ImageResponse } from 'next/og';
import { BRAND } from '../lib/brand';

export const alt = `${BRAND.name}: ${BRAND.tagline}`;
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';

export default function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: 80,
          background: 'linear-gradient(135deg, #080c1a 0%, #1c1f52 100%)',
          color: 'white',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <div
            style={{
              width: 128,
              height: 128,
              borderRadius: 34,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: 'linear-gradient(135deg, #5eead4, #818cf8)',
            }}
          >
            <svg width="76" height="76" viewBox="8 8 24 24" fill="none" stroke="#06101f" strokeWidth="3.4" strokeLinecap="round">
              <path d="M12 11v18M28 11v18" />
              <circle cx="20" cy="20" r="4.6" />
              <path d="M13.5 20h1.9M24.6 20h1.9" />
            </svg>
          </div>
          <div style={{ fontSize: 116, fontWeight: 800, letterSpacing: -4, marginLeft: 32 }}>{BRAND.name}</div>
        </div>
        <div style={{ fontSize: 42, color: '#a3accb', marginTop: 30 }}>
          {`${BRAND.tagline} Search jobs from every platform.`}
        </div>
      </div>
    ),
    size
  );
}
