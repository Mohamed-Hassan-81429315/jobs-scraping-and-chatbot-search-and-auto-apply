import { platformLabel } from '../lib/platforms';

const fmt = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  timeZone: 'UTC',
});

export default function JobCard({ job }) {
  const posted = job.posted_at ? new Date(job.posted_at) : null;
  const isNew = posted && Date.now() - posted.getTime() < 48 * 3600 * 1000;

  return (
    <article className="card">
      <header className="card-top">
        <span className="badge">{platformLabel(job.source)}</span>
        {isNew && <span className="new">New</span>}
        {job.remote && <span className="remote">Remote</span>}
        {posted && <time dateTime={posted.toISOString()}>{fmt.format(posted)}</time>}
      </header>

      <h3>
        <a href={job.url} target="_blank" rel="nofollow noopener noreferrer">
          {job.title}
          <span className="sr"> at {job.company} (opens in a new tab)</span>
        </a>
      </h3>

      <p className="meta">
        {job.company}
        {job.location ? ` · ${job.location}` : ''}
      </p>

      {job.excerpt && <p className="excerpt">{job.excerpt}</p>}

      {job.tags?.length > 0 && (
        <ul className="tags" aria-label="Skills and categories">
          {job.tags.map((t) => <li key={t} className="tag">{t}</li>)}
        </ul>
      )}
    </article>
  );
}
