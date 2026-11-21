import { BRAND } from '../lib/brand';

export default function manifest() {
  return {
    name: `${BRAND.name}: ${BRAND.tagline}`,
    short_name: BRAND.name,
    description: BRAND.description,
    start_url: '/',
    display: 'standalone',
    background_color: '#080c1a',
    theme_color: '#080c1a',
    icons: [{ src: '/icon.svg', sizes: 'any', type: 'image/svg+xml' }],
  };
}
