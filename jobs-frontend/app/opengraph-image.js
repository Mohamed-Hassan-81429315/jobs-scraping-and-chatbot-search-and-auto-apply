import { ImageResponse } from 'next/og';
import { BRAND } from '../lib/applyra-brand';

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
              borderRadius: 32,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: '#12263F',
            }}
          >
            <svg width="128" height="128" viewBox="0 0 40 40" fill="none">
              <rect width="40" height="40" rx="10" fill="#12263F" />
              <path d="M11.5 29.5 20 10.5l8.5 19" stroke="#ffffff" strokeWidth="3.6" strokeLinecap="round" strokeLinejoin="round" />
              <circle cx="20" cy="25" r="3.1" fill="#2EE6A6" />
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
