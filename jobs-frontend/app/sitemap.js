import { TRENDING } from '../lib/trending';

export default function sitemap() {
  const base = process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000';
  const now = new Date();

  return [
    { url: `${base}/`, lastModified: now, changeFrequency: 'daily', priority: 1 },
    { url: `${base}/?remote=1`, lastModified: now, changeFrequency: 'daily', priority: 0.8 },
    ...TRENDING.map((t) => ({
      url: `${base}/?q=${encodeURIComponent(t)}`,
      lastModified: now,
      changeFrequency: 'daily',
      priority: 0.7,
    })),
  ];
}
