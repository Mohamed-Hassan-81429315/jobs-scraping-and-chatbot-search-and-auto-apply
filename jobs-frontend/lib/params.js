import { platformLabel } from './platforms';

export const FILTER_KEYS = ['q', 'source', 'location', 'company', 'posted', 'remote', 'sort'];

const one = (v) => (Array.isArray(v) ? v[0] : v) || '';

export function normalize(sp = {}) {
  const page = parseInt(one(sp.page), 10);
  const sort = one(sp.sort);
  const posted = one(sp.posted);

  return {
    q: one(sp.q).trim().slice(0, 100),
    source: one(sp.source).slice(0, 100),
    location: one(sp.location).slice(0, 150),
    company: one(sp.company).slice(0, 255),
    posted: ['24h', '7d', '30d'].includes(posted) ? posted : '',
    remote: one(sp.remote) === '1' ? '1' : '',
    sort: sort === 'newest' || sort === 'relevance' ? sort : '',
    page: Number.isFinite(page) && page > 1 ? page : 1,
  };
}

/** Build a crawlable URL. Any change resets to page 1 unless a page is given. */
export function buildHref(params, overrides = {}) {
  const merged = { ...params, ...overrides };
  if (!('page' in overrides)) merged.page = 1;

  const usp = new URLSearchParams();
  for (const key of FILTER_KEYS) {
    if (merged[key]) usp.set(key, merged[key]);
  }
  if (merged.page > 1) usp.set('page', String(merged.page));

  const qs = usp.toString();
  return qs ? `/?${qs}` : '/';
}

export function hasFilters(p) {
  return Boolean(p.q || p.source || p.location || p.company || p.posted || p.remote);
}

export function headline(p) {
  let t = p.q ? `${p.q} jobs` : 'Jobs';
  if (p.remote) t = `Remote ${t}`;
  if (p.company) t += ` at ${p.company}`;
  if (p.location) t += ` in ${p.location}`;
  if (p.source) t += ` on ${platformLabel(p.source)}`;
  return t;
}
