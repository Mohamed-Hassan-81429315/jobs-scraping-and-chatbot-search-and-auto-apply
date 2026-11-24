import Link from 'next/link';
import { getJobs, getStats } from '../lib/server-api';
import { normalize, buildHref, headline, hasFilters } from '../lib/params';
import { TRENDING } from '../lib/trending';
import { BRAND } from '../lib/brand';
import { PLATFORMS } from '../lib/platforms';
import SearchPanel from '../components/SearchPanel';
import FiltersToggle from '../components/FiltersToggle';
import FilterSidebar from '../components/FilterSidebar';
import ActiveFilters from '../components/ActiveFilters';
import JobCard from '../components/JobCard';
import Pagination from '../components/Pagination';
import { getUser } from '../lib/auth';
import LoginView from '../components/auth/LoginView';

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000';

export async function generateMetadata({ searchParams }) {
  const sp = await searchParams;

  // Visitors who are not logged in see the login screen at "/".
  if (!(await getUser())) {
    return {
      title: 'Log in or create your account',
      alternates: { canonical: '/' },
      robots: { index: true, follow: true },
    };
  }

  const p = normalize(sp);

  // A saved conversation (?chat=ID) or a fresh chat (?new=...) is private: never index it.
  if (sp?.chat || sp?.new) {
    return { alternates: { canonical: '/' }, robots: { index: false, follow: false } };
  }

  if (!hasFilters(p) && p.page === 1 && !p.sort) {
    return { alternates: { canonical: '/' } };
  }

  // Index search pages with at most one facet; keep the rest out of the index.
  const facetCount = [p.location, p.company, p.source, p.remote].filter(Boolean).length;
  const noindex = p.page > 1 || Boolean(p.sort) || Boolean(p.posted) || facetCount > 1;

  const canonical = buildHref({
    q: p.q, location: p.location, company: p.company, source: p.source, remote: p.remote,
  });
  const base = headline(p);
  const title = p.page > 1 ? `${base} (page ${p.page})` : base;
  const description = `Browse ${base.toLowerCase()} collected from multiple job platforms. Filter by location, company and date posted, then apply on the original site.`;

  return {
    title,
    description,
    alternates: { canonical },
    robots: { index: !noindex, follow: true },
    openGraph: { title, description, url: canonical, type: 'website' },
  };
}

export default async function Home({ searchParams }) {
  const sp = await searchParams;

  // Login is the front door: guests get the login screen, logged-in users get the job search.
  if (!(await getUser())) return <LoginView params={sp} />;

  const p = normalize(sp);

  let stats = null;
  let data = null;
  let failed = false;

  try {
    [stats, data] = await Promise.all([getStats(), getJobs(p)]);
  } catch {
    failed = true;
  }

  const facets = {
    sources: data?.facets?.sources ?? (stats?.by_source ?? []).map((s) => ({ key: s.name, count: s.count })),
    locations: data?.facets?.locations ?? [],
    companies: data?.facets?.companies ?? [],
    posted: data?.facets?.posted ?? {},
    remote: data?.facets?.remote ?? 0,
  };

  const total = data?.total ?? 0;
  const jobs = data?.data ?? [];
  const filtered = hasFilters(p);
  const activeCount = [p.location, p.company, p.source, p.posted, p.remote].filter(Boolean).length;
  const counts = Object.fromEntries((stats?.by_source ?? []).map((s) => [s.name, s.count]));
  const effectiveSort = p.sort || (p.q ? 'relevance' : 'newest');
  const perPage = data?.per_page ?? 12;

  const jsonLd = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'WebSite',
        '@id': `${SITE_URL}/#website`,
        url: SITE_URL,
        name: BRAND.name,
        potentialAction: {
          '@type': 'SearchAction',
          target: { '@type': 'EntryPoint', urlTemplate: `${SITE_URL}/?q={search_term_string}` },
          'query-input': 'required name=search_term_string',
        },
      },
      ...(jobs.length
        ? [{
            '@type': 'ItemList',
            itemListElement: jobs.map((j, i) => ({
              '@type': 'ListItem',
              position: (p.page - 1) * perPage + i + 1,
              url: j.url,
              name: `${j.title} at ${j.company}`,
            })),
          }]
        : []),
    ],
  };

  return (
    <main id="main">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, '\\u003c') }}
      />

      <section className="hero wrap" aria-labelledby="page-title">
        <p className="eyebrow">Job search engine</p>
        <h1 id="page-title">
          {filtered ? headline(p) : <>Find your next role. <em>Every platform, one search.</em></>}
        </h1>
        <p className="sub">
          Search openings collected from many job platforms, filter them like a pro, and apply on the original site.
        </p>

        <SearchPanel params={p} />

        <ul className="trending" aria-label="Popular searches">
          <li><span>Trending:</span></li>
          {TRENDING.slice(0, 6).map((t) => (
            <li key={t}>
              <Link href={buildHref({}, { q: t })} prefetch={false}>{t}</Link>
            </li>
          ))}
        </ul>

        {stats && (
          <ul className="stats" aria-label="Database statistics">
            <li><strong>{stats.total_jobs.toLocaleString('en-US')}</strong><span>jobs</span></li>
            <li><strong>{stats.total_companies.toLocaleString('en-US')}</strong><span>companies</span></li>
            <li><strong>{stats.by_source.length}</strong><span>platforms</span></li>
          </ul>
        )}
      </section>

      <section className="platforms wrap" aria-labelledby="platforms-title">
        <h2 id="platforms-title">Platforms we search</h2>
        <ul>
          {PLATFORMS.map((pl) => {
            const n = counts[pl.key] || 0;
            return (
              <li key={pl.key}>
                {n > 0 ? (
                  <Link href={buildHref({}, { source: pl.key })} prefetch={false} className="plat">
                    {pl.label} <em>{n.toLocaleString('en-US')}</em>
                  </Link>
                ) : (
                  <span className="plat off" title="No jobs collected yet">{pl.label}</span>
                )}
              </li>
            );
          })}
        </ul>
      </section>

      <div id="results" className="results-layout wrap" tabIndex={-1}>
        <FiltersToggle activeCount={activeCount}>
          <FilterSidebar params={p} facets={facets} />
        </FiltersToggle>

        <section className="results-main" aria-labelledby="results-title">
          <div className="results-head">
            <h2 id="results-title">
              {failed ? 'Jobs' : `${total.toLocaleString('en-US')} ${total === 1 ? 'job' : 'jobs'} found`}
            </h2>
            {!failed && total > 0 && (
              <nav className="sort" aria-label="Sort results">
                {p.q && (
                  <Link
                    href={buildHref(p, { sort: 'relevance' })}
                    aria-current={effectiveSort === 'relevance' ? 'true' : undefined}
                    prefetch={false}
                    scroll={false}
                  >
                    Best match
                  </Link>
                )}
                <Link
                  href={buildHref(p, { sort: 'newest' })}
                  aria-current={effectiveSort === 'newest' ? 'true' : undefined}
                  prefetch={false}
                  scroll={false}
                >
                  Newest
                </Link>
              </nav>
            )}
          </div>

          <ActiveFilters params={p} />

          {failed && (
            <div className="empty" role="alert">
              <h3>We couldn’t load jobs right now</h3>
              <p>The search service isn’t responding. Please try again in a moment.</p>
              <Link className="btn-link" href={buildHref(p, {})} prefetch={false}>Try again</Link>
            </div>
          )}

          {!failed && total === 0 && (
            <div className="empty">
              <h3>No jobs match your search</h3>
              <p>Try fewer words, check the spelling, or remove a filter.</p>
              <ul className="trending">
                {TRENDING.slice(0, 5).map((t) => (
                  <li key={t}><Link href={buildHref({}, { q: t })} prefetch={false}>{t}</Link></li>
                ))}
              </ul>
              <Link className="btn-link" href="/" prefetch={false}>Clear all filters</Link>
            </div>
          )}

          {jobs.length > 0 && (
            <div className="grid">
              {jobs.map((job) => <JobCard key={job.id} job={job} />)}
            </div>
          )}

          {data && <Pagination params={p} current={data.current_page} last={data.last_page} />}
        </section>
      </div>
    </main>
  );
}