#!/usr/bin/env python3
"""
Frontend patch for JobScope. Run from inside the jobs-frontend folder:

    python3 patch_frontend.py

1. Recent searches can be removed one by one (x button, or Delete key).
2. Platforms get proper names (LinkedIn, Indeed, Glassdoor, Odoo, ...), and a
   "Platforms we search" strip is shown on the home page.

All edits are verified first; nothing is written unless every one matches.
Originals are saved next to each file as <name>.prepatch.
"""
import pathlib
import shutil
import sys

if not pathlib.Path("app/page.js").exists():
    sys.exit("Run this from the jobs-frontend folder (app/page.js not found).")

edits = {}


def edit(path, old, new):
    edits.setdefault(path, []).append((old, new))


# ---------------------------------------------------------------- new module
PLATFORMS_JS = """export const PLATFORMS = [
  { key: 'linkedin', label: 'LinkedIn' },
  { key: 'indeed', label: 'Indeed' },
  { key: 'glassdoor', label: 'Glassdoor' },
  { key: 'odoo', label: 'Odoo' },
  { key: 'smartrecruiters', label: 'SmartRecruiters' },
  { key: 'epam', label: 'EPAM' },
  { key: 'remoteok', label: 'RemoteOK' },
  { key: 'remotive', label: 'Remotive' },
  { key: 'arbeitnow', label: 'Arbeitnow' },
];

const LABELS = Object.fromEntries(PLATFORMS.map((p) => [p.key, p.label]));

export function platformLabel(key) {
  return LABELS[key] || key;
}
"""

# ------------------------------------------------------------------- params
edit("lib/params.js",
     "export const FILTER_KEYS = [",
     "import { platformLabel } from './platforms';\n\nexport const FILTER_KEYS = [")
edit("lib/params.js",
     "if (p.source) t += ` on ${p.source}`;",
     "if (p.source) t += ` on ${platformLabel(p.source)}`;")

# ------------------------------------------------------------------ JobCard
edit("components/JobCard.js",
     "const fmt = new Intl.DateTimeFormat('en-GB', {",
     "import { platformLabel } from '../lib/platforms';\n\nconst fmt = new Intl.DateTimeFormat('en-GB', {")
edit("components/JobCard.js",
     '<span className="badge">{job.source}</span>',
     '<span className="badge">{platformLabel(job.source)}</span>')

# ------------------------------------------------------------ FilterSidebar
edit("components/FilterSidebar.js",
     "import { buildHref } from '../lib/params';",
     "import { buildHref } from '../lib/params';\nimport { platformLabel } from '../lib/platforms';")
edit("components/FilterSidebar.js",
     "<Option key={s.key} href={toggle('source', s.key)} label={s.key} count={s.count} selected={params.source === s.key} cap />",
     "<Option key={s.key} href={toggle('source', s.key)} label={platformLabel(s.key)} count={s.count} selected={params.source === s.key} />")

# ------------------------------------------------------------ ActiveFilters
edit("components/ActiveFilters.js",
     "import { buildHref } from '../lib/params';",
     "import { buildHref } from '../lib/params';\nimport { platformLabel } from '../lib/platforms';")
edit("components/ActiveFilters.js",
     "chips.push(['Platform', params.source, { source: '' }]);",
     "chips.push(['Platform', platformLabel(params.source), { source: '' }]);")

# -------------------------------------------------------------- SearchPanel
SP = "components/SearchPanel.js"
edit(SP,
     "function clearRecent() {",
     "function removeRecent(term) {\n"
     "  try {\n"
     "    const next = loadRecent().filter((t) => t !== term);\n"
     "    localStorage.setItem(RECENT_KEY, JSON.stringify(next));\n"
     "  } catch {}\n"
     "}\n\n"
     "function clearRecent() {")
edit(SP,
     "...recent.map((label) => ({ type: 'query', icon: 'clock', label, group: 'Recent searches' })),",
     "...recent.map((label) => ({ type: 'query', icon: 'clock', label, group: 'Recent searches', removable: true })),")
edit(SP,
     "    } else if (e.key === 'Escape') {",
     "    } else if (e.key === 'Delete' && active >= 0 && items[active]?.removable) {\n"
     "      e.preventDefault();\n"
     "      forget(items[active].label);\n"
     "    } else if (e.key === 'Escape') {")
edit(SP,
     "const hasRecent = term.length < 2 && recent.length > 0;",
     "function forget(label) {\n"
     "    removeRecent(label);\n"
     "    setRecent(loadRecent());\n"
     "    setActive(-1);\n"
     "  }\n\n"
     "  const hasRecent = term.length < 2 && recent.length > 0;")
edit(SP,
     "<span><Highlight text={it.label} term={term.length >= 2 ? term : ''} /></span>",
     "<span className=\"sg-label\"><Highlight text={it.label} term={term.length >= 2 ? term : ''} /></span>\n"
     "                  {it.removable && (\n"
     "                    <button\n"
     "                      type=\"button\"\n"
     "                      className=\"sg-remove\"\n"
     "                      tabIndex={-1}\n"
     "                      title=\"Remove from recent searches\"\n"
     "                      aria-label={`Remove ${it.label} from recent searches`}\n"
     "                      onPointerDown={(e) => {\n"
     "                        e.preventDefault();\n"
     "                        e.stopPropagation();\n"
     "                        forget(it.label);\n"
     "                      }}\n"
     "                    >\n"
     "                      ×\n"
     "                    </button>\n"
     "                  )}")

# --------------------------------------------------------------------- page
edit("app/page.js",
     "import { TRENDING } from '../lib/trending';",
     "import { TRENDING } from '../lib/trending';\nimport { PLATFORMS } from '../lib/platforms';")
edit("app/page.js",
     "const effectiveSort = p.sort || (p.q ? 'relevance' : 'newest');",
     "const counts = Object.fromEntries((stats?.by_source ?? []).map((s) => [s.name, s.count]));\n"
     "  const effectiveSort = p.sort || (p.q ? 'relevance' : 'newest');")
edit("app/page.js",
     '<div id="results" className="results-layout wrap" tabIndex={-1}>',
     '<section className="platforms wrap" aria-labelledby="platforms-title">\n'
     '        <h2 id="platforms-title">Platforms we search</h2>\n'
     '        <ul>\n'
     '          {PLATFORMS.map((pl) => {\n'
     '            const n = counts[pl.key] || 0;\n'
     '            return (\n'
     '              <li key={pl.key}>\n'
     '                {n > 0 ? (\n'
     '                  <Link href={buildHref({}, { source: pl.key })} prefetch={false} className="plat">\n'
     '                    {pl.label} <em>{n.toLocaleString(\'en-US\')}</em>\n'
     '                  </Link>\n'
     '                ) : (\n'
     '                  <span className="plat off" title="No jobs collected yet">{pl.label}</span>\n'
     '                )}\n'
     '              </li>\n'
     '            );\n'
     '          })}\n'
     '        </ul>\n'
     '      </section>\n\n'
     '      <div id="results" className="results-layout wrap" tabIndex={-1}>')

CSS = """
/* platforms strip + removable recent searches */
.platforms { text-align: center; padding-bottom: 8px; }
.platforms h2 { font-size: .78rem; letter-spacing: .14em; text-transform: uppercase; color: var(--muted); font-weight: 600; margin-bottom: 12px; }
.platforms ul { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; }
.plat { display: inline-flex; align-items: center; gap: 8px; padding: 8px 16px; border-radius: 999px; font-size: .9rem; font-weight: 600; background: var(--panel); border: 1px solid var(--line); }
a.plat:hover { border-color: rgba(94, 234, 212, .5); }
.plat em { font-style: normal; font-weight: 500; font-size: .78rem; color: var(--muted); font-variant-numeric: tabular-nums; }
.plat.off { opacity: .45; font-weight: 500; }
.sg-label { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sg-remove { flex: none; width: 28px; height: 28px; border-radius: 8px; border: 0; cursor: pointer; background: transparent; color: var(--muted); font-size: 1.25rem; line-height: 1; opacity: 0; transition: opacity .15s, background .15s; }
.sg-item:hover .sg-remove, .sg-item[aria-selected="true"] .sg-remove { opacity: 1; }
.sg-remove:hover { background: rgba(244, 114, 182, .18); color: #fbcfe8; }
@media (hover: none) { .sg-remove { opacity: 1; } }
"""

# ------------------------------------------------------------------- apply
problems = []
updated = {}

for path, pairs in edits.items():
    file = pathlib.Path(path)
    if not file.exists():
        problems.append(f"{path}: file not found")
        continue
    text = file.read_text(encoding="utf-8")
    for old, new in pairs:
        count = text.count(old)
        if count != 1:
            problems.append(f"{path}: expected 1 match, found {count} for: {old[:70]!r}")
        else:
            text = text.replace(old, new)
    updated[path] = text

css_file = pathlib.Path("app/globals.css")
if not css_file.exists():
    problems.append("app/globals.css: file not found")
elif "platforms strip" in css_file.read_text(encoding="utf-8"):
    problems.append("app/globals.css: already patched")

if pathlib.Path("lib/platforms.js").exists():
    problems.append("lib/platforms.js: already exists (patch already applied?)")

if problems:
    print("Nothing was changed. Problems found:")
    for p in problems:
        print("  -", p)
    sys.exit(1)

for path, text in updated.items():
    shutil.copy2(path, path + ".prepatch")
    pathlib.Path(path).write_text(text, encoding="utf-8")

shutil.copy2(css_file, str(css_file) + ".prepatch")
with css_file.open("a", encoding="utf-8") as handle:
    handle.write(CSS)

pathlib.Path("lib/platforms.js").write_text(PLATFORMS_JS, encoding="utf-8")
print("Patched OK:", ", ".join(sorted(updated)), "+ app/globals.css + lib/platforms.js")
