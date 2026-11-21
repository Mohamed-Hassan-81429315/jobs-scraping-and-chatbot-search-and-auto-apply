import Link from 'next/link';
import { buildHref } from '../lib/params';

function windowPages(current, last) {
  const set = new Set([1, last, current - 2, current - 1, current, current + 1, current + 2]);
  const pages = [...set].filter((n) => n >= 1 && n <= last).sort((a, b) => a - b);
  const out = [];
  pages.forEach((n, i) => {
    if (i && n - pages[i - 1] > 1) out.push(`gap-${n}`);
    out.push(n);
  });
  return out;
}

export default function Pagination({ params, current, last }) {
  if (last <= 1) return null;

  return (
    <nav className="pager" aria-label="Pagination">
      {current > 1 ? (
        <Link href={buildHref(params, { page: current - 1 })} rel="prev" prefetch={false}>← Previous</Link>
      ) : (
        <span className="pg" aria-disabled="true">← Previous</span>
      )}

      <ol>
        {windowPages(current, last).map((n) =>
          typeof n === 'number' ? (
            <li key={n}>
              {n === current ? (
                <span className="pg" aria-current="page">{n}</span>
              ) : (
                <Link href={buildHref(params, { page: n })} prefetch={false} aria-label={`Page ${n}`}>{n}</Link>
              )}
            </li>
          ) : (
            <li key={n} aria-hidden="true"><span className="pg">…</span></li>
          )
        )}
      </ol>

      {current < last ? (
        <Link href={buildHref(params, { page: current + 1 })} rel="next" prefetch={false}>Next →</Link>
      ) : (
        <span className="pg" aria-disabled="true">Next →</span>
      )}
    </nav>
  );
}
