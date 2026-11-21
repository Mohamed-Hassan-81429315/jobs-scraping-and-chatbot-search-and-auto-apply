const BASE = process.env.API_INTERNAL_URL || 'http://127.0.0.1:8000/api';

async function get(path, params = {}) {
  const url = new URL(BASE + path);
  for (const [k, v] of Object.entries(params)) {
    if (v !== '' && v != null) url.searchParams.set(k, String(v));
  }
  const res = await fetch(url, { cache: 'no-store', headers: { Accept: 'application/json' } });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

export const getStats = () => get('/stats');
export const getJobs = (params) => get('/jobs', params);
