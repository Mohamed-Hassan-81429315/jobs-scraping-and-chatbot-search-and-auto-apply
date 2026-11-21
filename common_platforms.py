"""
common_platforms.py - well-known platforms.

  odoo      Odoo's public careers pages (robots.txt is checked first; jobs
            already in jobs.json are skipped before their page is requested).
  linkedin / indeed / glassdoor
            Collected through a licensed job-data API (JSearch on RapidAPI /
            OpenWeb Ninja) with YOUR API key. These sites forbid direct
            scraping, so nothing here touches them directly.

Usage:
    python common_platforms.py                      # everything
    python common_platforms.py --only odoo
    python common_platforms.py --only odoo --refresh-odoo   # re-read known Odoo jobs
    python common_platforms.py --debug-odoo software-developer-1
    python common_platforms.py --only jsearch --max-requests 5
"""
import argparse
import hashlib
import html as htmllib
import json
import os
import re
import time
from collections import Counter
from datetime import datetime, timezone
from urllib import robotparser

import requests

from job_aggregator import DATE_UNTIL, HEADERS, REQUEST_TIMEOUT, SINCE, job, parse_date
from run_smartrecruiters import load_jobs, save_jobs

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USER_AGENT = HEADERS["User-Agent"]

# ----------------------------------------------------------------- settings


def setting(name, default=""):
    """Read a setting from the environment or from common_platforms.env."""
    if os.environ.get(name):
        return os.environ[name]
    path = os.path.join(BASE_DIR, "common_platforms.env")
    try:
        with open(path, encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    if key.strip() == name:
                        return value.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return default


def in_range(posted):
    return posted is None or (SINCE <= posted <= DATE_UNTIL)


def get_html(session, url, retries=3):
    for attempt in range(retries):
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT)
            if response.status_code == 404:
                return None
            if response.status_code == 429:
                try:
                    wait = int(response.headers.get("Retry-After", ""))
                except ValueError:
                    wait = 2 ** attempt * 5
                time.sleep(wait)
                continue
            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:
            if attempt == retries - 1:
                print(f"[warn] {url}: {exc}")
            else:
                time.sleep(2 ** attempt)
    return None


def load_robots(session, base):
    """Return a robots.txt parser, or None when it can't be read (be conservative)."""
    parser = robotparser.RobotFileParser()
    try:
        response = session.get(f"{base}/robots.txt", timeout=REQUEST_TIMEOUT)
    except requests.RequestException:
        return None
    if response.status_code == 404:
        parser.parse([])
        return parser
    if response.status_code != 200:
        return None
    parser.parse(response.text.splitlines())
    return parser


# --------------------------------------------------------------------- Odoo

ODOO_BASE = "https://www.odoo.com"
ODOO_LIST = f"{ODOO_BASE}/en_US/jobs"
ODOO_SLUG_RE = re.compile(r"/jobs/(?:detail/)?([a-z0-9][a-z0-9-]*-\d+)")


def odoo_collect(session, robots, max_pages=30):
    slugs = []
    seen = set()
    for page in range(1, max_pages + 1):
        url = ODOO_LIST if page == 1 else f"{ODOO_LIST}/page/{page}"
        if not robots.can_fetch(USER_AGENT, url):
            print(f"[skip] Odoo: robots.txt disallows {url}")
            break
        html = get_html(session, url)
        if not html:
            break
        new = [s for s in dict.fromkeys(ODOO_SLUG_RE.findall(html)) if s not in seen]
        if not new:
            break
        seen.update(new)
        slugs.extend(new)
        time.sleep(1)
    return slugs


def ld_location(data):
    place = data.get("jobLocation")
    if isinstance(place, list):
        place = place[0] if place else None
    address = place.get("address") if isinstance(place, dict) else None
    if not isinstance(address, dict):
        return None
    country = address.get("addressCountry")
    if isinstance(country, dict):
        country = country.get("name")
    parts = [address.get("addressLocality"), address.get("addressRegion"), country]
    return ", ".join(str(p) for p in parts if p) or None


def html_lines(fragment):
    """Visible text of an HTML fragment as a list of non-empty lines."""
    fragment = re.sub(r"(?is)<(script|style|noscript|svg)\b.*?</\1>", " ", fragment)
    fragment = re.sub(r"(?i)<br\s*/?>", "\n", fragment)
    fragment = re.sub(
        r"(?i)</(p|div|li|h[1-6]|section|address|tr|td|button|article|header|footer|ul|ol)>",
        "\n", fragment,
    )
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    text = htmllib.unescape(fragment)
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return [line for line in lines if line]


def odoo_title(html):
    patterns = (
        r"<h1[^>]*>(.*?)</h1>",
        r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)',
        r"<title>(.*?)</title>",
    )
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.S | re.I)
        if match:
            title = htmllib.unescape(re.sub(r"<[^>]+>", " ", match.group(1)))
            title = re.sub(r"\s+", " ", title).strip()
            title = re.sub(r"\s*[|\-]\s*Odoo\s*$", "", title)
            if title:
                return title
    return None


def odoo_department_location(html, title):
    """Read department and office address from the page.

    Odoo job pages show: title, department, address, then an 'Apply' button.
    A real <address> element is used when present.
    """
    location = None
    address = re.search(r"(?is)<address\b[^>]*>(.*?)</address>", html)
    if address:
        parts = html_lines(address.group(1))
        if parts:
            location = ", ".join(parts[:4])

    lines = html_lines(html)
    start = next((i for i, line in enumerate(lines) if line == title), None)
    if start is None and title:
        start = next((i for i, line in enumerate(lines) if title in line), None)
    begin = start + 1 if start is not None else 0
    stop = next(
        (i for i in range(begin, min(len(lines), begin + 15)) if lines[i].lower() == "apply"),
        None,
    )

    department = None
    if stop is not None:
        between = [line for line in lines[begin:stop] if len(line) < 200]
        if len(between) >= 2:
            department = between[0]
            if not location:
                location = ", ".join(between[1:4])
        elif len(between) == 1 and not location and re.search(r"[,\d]", between[0]):
            location = between[0]
    return department, location


def odoo_posted(html):
    patterns = (
        r'property=["\']article:published_time["\'][^>]*content=["\']([^"\']+)',
        r'content=["\']([^"\']+)["\'][^>]*property=["\']article:published_time',
        r'"datePosted"\s*:\s*"([^"]+)"',
        r'<time[^>]+datetime=["\']([^"\']+)',
    )
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.I)
        if match:
            parsed = parse_date(match.group(1))
            if parsed:
                return parsed
    return None


def odoo_parse(url, html):
    posting = None
    block_pattern = r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>'
    for block in re.findall(block_pattern, html, flags=re.S | re.I):
        try:
            data = json.loads(block.strip())
        except json.JSONDecodeError:
            continue
        for item in (data if isinstance(data, list) else [data]):
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                posting = item

    if posting:
        tags = []
        employment = posting.get("employmentType")
        tags.extend(employment if isinstance(employment, list) else [employment] if employment else [])
        if posting.get("jobLocationType") == "TELECOMMUTE":
            tags.append("Remote")
        return job(
            "odoo", posting.get("title"), "Odoo", ld_location(posting), url,
            parse_date(posting.get("datePosted")), posting.get("description"),
            [str(t) for t in tags],
        )

    title = odoo_title(html)
    if not title:
        return None
    department, location = odoo_department_location(html, title)
    meta = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']*)', html, flags=re.I
    )
    description = htmllib.unescape(meta.group(1)) if meta else None
    return job(
        "odoo", title, "Odoo", location, url, odoo_posted(html), description,
        [department] if department else [],
    )


def fetch_odoo(known_urls, limit=0, refresh=False):
    session = requests.Session()
    session.headers.update(HEADERS)

    robots = load_robots(session, ODOO_BASE)
    if robots is None:
        print("[skip] Odoo: robots.txt could not be read, so nothing was fetched")
        return

    slugs = odoo_collect(session, robots)
    urls = [f"{ODOO_BASE}/en_US/jobs/{slug}" for slug in slugs]
    todo = urls if refresh else [u for u in urls if u not in known_urls]
    if limit:
        todo = todo[:limit]
    mode = "refreshing all" if refresh else "new only"
    print(f"Odoo: {len(urls)} jobs listed, {len(todo)} to fetch ({mode})")

    for url in todo:
        if not robots.can_fetch(USER_AGENT, url):
            continue
        html = get_html(session, url)
        if html:
            record = odoo_parse(url, html)
            if record:
                yield record
        time.sleep(0.7)


def debug_odoo(slug):
    """Show exactly what the parser sees on one Odoo job page."""
    session = requests.Session()
    session.headers.update(HEADERS)
    robots = load_robots(session, ODOO_BASE)
    if robots is None:
        print("robots.txt could not be read")
        return
    url = f"{ODOO_BASE}/en_US/jobs/{slug}"
    if not robots.can_fetch(USER_AGENT, url):
        print("robots.txt disallows this page")
        return
    html = get_html(session, url)
    if not html:
        print("page could not be fetched")
        return
    print("URL:", url)
    print("JSON-LD blocks :", len(re.findall(r"application/ld\+json", html)))
    print("<address> tags :", len(re.findall(r"<address\b", html, flags=re.I)))
    record = odoo_parse(url, html)
    if record:
        print("title          :", record["title"])
        print("location       :", record["location"])
        print("posted_at      :", record["posted_at"])
        print("tags           :", record["tags"])
    title = record["title"] if record else None
    lines = html_lines(html)
    start = next((i for i, line in enumerate(lines) if title and (line == title or title in line)), 0)
    print("\n--- text lines after the title ---")
    for line in lines[start:start + 14]:
        print("  |", line[:120])


# ------------------------------------------- LinkedIn / Indeed / Glassdoor

JSEARCH_URL = "https://jsearch.p.rapidapi.com/search"
JSEARCH_HOST = "jsearch.p.rapidapi.com"
WANTED = ("linkedin", "indeed", "glassdoor")
DEFAULT_QUERIES = ["software engineer", "odoo developer", "data analyst", "project manager"]


class ApiStop(Exception):
    """Raised when the API says to stop (bad key, no subscription, quota)."""


def load_queries(path):
    try:
        with open(path, encoding="utf-8") as file:
            queries = [l.strip() for l in file if l.strip() and not l.lstrip().startswith("#")]
        return queries or DEFAULT_QUERIES
    except FileNotFoundError:
        return DEFAULT_QUERIES


def detect_platform(item):
    names = [item.get("job_publisher") or ""]
    names += [(o or {}).get("publisher") or "" for o in item.get("apply_options") or []]
    for name in names:
        for key in WANTED:
            if key in name.lower():
                return key
    return None


def jsearch_request(session, params, retries=3):
    for attempt in range(retries):
        try:
            response = session.get(JSEARCH_URL, params=params, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as exc:
            if attempt == retries - 1:
                raise ApiStop(f"network error: {exc}")
            time.sleep(2 ** attempt)
            continue
        if response.status_code in (401, 403):
            detail = response.text.strip().replace("\n", " ")[:200]
            raise ApiStop(
                "API key rejected or not subscribed to JSearch (HTTP %d): %s"
                % (response.status_code, detail)
            )
        if response.status_code == 429:
            if attempt == retries - 1:
                raise ApiStop("rate limit or monthly quota reached (HTTP 429)")
            time.sleep(2 ** attempt * 5)
            continue
        if response.status_code >= 500:
            time.sleep(2 ** attempt)
            continue
        response.raise_for_status()
        try:
            return response.json()
        except ValueError:
            return None
    return None


def jsearch_record(item, platform):
    url = item.get("job_apply_link") or ""
    for option in item.get("apply_options") or []:
        if platform in ((option or {}).get("publisher") or "").lower() and option.get("apply_link"):
            url = option["apply_link"]
            break
    if not url or not item.get("job_title"):
        return None

    posted = parse_date(item.get("job_posted_at_datetime_utc"))
    if not in_range(posted):
        return None

    location = ", ".join(
        str(p) for p in (item.get("job_city"), item.get("job_state"), item.get("job_country")) if p
    ) or None

    tags = [str(t).replace("_", " ").title() for t in (item.get("job_employment_types") or []) if t]
    if item.get("job_is_remote"):
        tags.append("Remote")

    record = job(
        platform, item["job_title"], item.get("employer_name"), location, url, posted,
        item.get("job_description"), tags,
        {"job_id": item.get("job_id"), "publisher": item.get("job_publisher")},
    )
    stable = item.get("job_id") or url
    record["id"] = hashlib.md5(f"{platform}|{stable}".encode("utf-8")).hexdigest()
    return record


def fetch_jsearch(api_key, queries, pages, date_posted, max_requests):
    session = requests.Session()
    session.headers.update({
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": JSEARCH_HOST,
        "Accept": "application/json",
    })

    used = 0
    for query in queries:
        for page in range(1, pages + 1):
            if used >= max_requests:
                print(f"JSearch: request cap of {max_requests} reached, stopping")
                return
            params = {"query": query, "page": page, "num_pages": 1, "date_posted": date_posted}
            try:
                data = jsearch_request(session, params)
            except ApiStop as exc:
                print(f"[stop] JSearch: {exc}")
                return
            used += 1

            items = (data or {}).get("data") or []
            kept = 0
            for item in items:
                platform = detect_platform(item)
                if not platform:
                    continue
                record = jsearch_record(item, platform)
                if record:
                    kept += 1
                    yield record
            print(f"JSearch '{query}' page {page}: {len(items)} results, {kept} from {', '.join(WANTED)}")
            if not items:
                break
            time.sleep(0.5)


# --------------------------------------------------------------------- main


def main():
    parser = argparse.ArgumentParser(description="Collect Odoo, LinkedIn, Indeed and Glassdoor jobs.")
    parser.add_argument("--only", choices=["odoo", "jsearch"], help="run just one source")
    parser.add_argument("--out", default="jobs.json")
    parser.add_argument("--queries", default=os.path.join(BASE_DIR, "common_platforms_queries.txt"))
    parser.add_argument("--pages", type=int, default=1, help="result pages per query")
    parser.add_argument("--date-posted", default="3days", choices=["all", "today", "3days", "week", "month"])
    parser.add_argument("--max-requests", type=int, default=20, help="API calls allowed per run")
    parser.add_argument("--odoo-limit", type=int, default=0, help="max Odoo jobs per run (0 = all)")
    parser.add_argument("--refresh-odoo", action="store_true", help="re-read Odoo jobs already stored")
    parser.add_argument("--debug-odoo", metavar="SLUG", help="inspect one Odoo job page, e.g. software-developer-1")
    args = parser.parse_args()

    if args.debug_odoo:
        debug_odoo(args.debug_odoo)
        return

    jobs = load_jobs(args.out)
    added = Counter()
    updated = Counter()
    now_iso = datetime.now(timezone.utc).isoformat()

    def merge(record):
        bucket = updated if record["id"] in jobs else added
        bucket[record["source"]] += 1
        jobs[record["id"]] = record

    if args.only in (None, "odoo"):
        existing = {j.get("url"): j for j in jobs.values() if j.get("source") == "odoo"}
        try:
            for record in fetch_odoo(set(existing), args.odoo_limit, args.refresh_odoo):
                previous = existing.get(record["url"])
                # Keep the same id for a known job, even if its title was re-parsed.
                record["id"] = previous["id"] if previous else hashlib.md5(
                    f"odoo|{record['url']}".encode("utf-8")
                ).hexdigest()
                # Odoo shows no posting date: use the date we first saw the job.
                if not record["posted_at"]:
                    record["posted_at"] = (previous or {}).get("posted_at") or now_iso
                    record["posted_at_source"] = "first_seen"
                if in_range(parse_date(record["posted_at"])):
                    merge(record)
        except Exception as exc:
            print(f"[error] Odoo: {exc}")
        save_jobs(args.out, jobs)

    if args.only in (None, "jsearch"):
        key = setting("JSEARCH_API_KEY")
        if not key:
            print("[skip] LinkedIn/Indeed/Glassdoor: set JSEARCH_API_KEY in common_platforms.env")
        else:
            try:
                for record in fetch_jsearch(
                    key, load_queries(args.queries), max(1, args.pages),
                    args.date_posted, max(1, args.max_requests),
                ):
                    merge(record)
            except Exception as exc:
                print(f"[error] JSearch: {exc}")
            save_jobs(args.out, jobs)

    print(f"Done: {sum(added.values())} new jobs ({dict(added) or 'none'}), "
          f"{sum(updated.values())} refreshed. {len(jobs)} jobs in {args.out}")


if __name__ == "__main__":
    main()
