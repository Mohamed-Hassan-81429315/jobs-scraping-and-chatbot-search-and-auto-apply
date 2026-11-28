#!/usr/bin/env python3
"""
scrape_jobboards.py - LinkedIn, Indeed and Glassdoor jobs via a licensed API.

These sites forbid direct scraping, so this uses JSearch (RapidAPI / OpenWeb
Ninja) with YOUR API key. Results are merged into jobs.json using the same
record format as job_aggregator.py, so the existing validate -> import -> index
steps of daily_pipeline.sh pick them up unchanged.

Setup:
    pip install requests
    echo 'JSEARCH_API_KEY=your_key' > common_platforms.env
    # one search per line (lines starting with # are ignored):
    echo 'odoo developer' >> common_platforms_queries.txt

Usage:
    python scrape_jobboards.py
    python scrape_jobboards.py --query "python developer in Cairo" --country eg
    python scrape_jobboards.py --platforms linkedin,indeed --date-posted week
    python scrape_jobboards.py --max-requests 5 --dry-run

Exit codes: 0 = ok, 1 = unexpected error, 2 = API refused us (bad key, no
subscription or quota used up) - so daily_pipeline.sh can mark the step FAILED.
"""

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone

import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
API_URL = "https://jsearch.p.rapidapi.com/search"
API_HOST = "jsearch.p.rapidapi.com"
ALL_PLATFORMS = ("linkedin", "indeed", "glassdoor")
DEFAULT_QUERIES = ["software engineer", "odoo developer", "data analyst", "project manager"]
TIMEOUT = 30


class ApiStop(Exception):
    """The API told us to stop (bad key, not subscribed, quota exhausted)."""


# ---------------------------------------------------------------- settings
def setting(name, default=""):
    """Read from the environment first, then from common_platforms.env."""
    if os.environ.get(name):
        return os.environ[name]
    try:
        with open(os.path.join(BASE_DIR, "common_platforms.env"), encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    if key.strip() == name:
                        return value.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return default


def looks_like_placeholder(key):
    """True for obvious fake values such as PASTE_YOUR_KEY_HERE or your_real_key."""
    k = key.strip().lower()
    fake_words = ("paste", "your_", "your-", "real_key", "api_key_here", "xxxx", "changeme", "example")
    return len(k) < 30 or any(w in k for w in fake_words)


def load_queries(path):
    try:
        with open(path, encoding="utf-8") as f:
            queries = [l.strip() for l in f if l.strip() and not l.lstrip().startswith("#")]
        return queries or DEFAULT_QUERIES
    except FileNotFoundError:
        return DEFAULT_QUERIES


# ----------------------------------------------------------------- helpers
def parse_date(value):
    if not value:
        return None
    try:
        text = str(value).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def detect_platform(item, wanted):
    """Return linkedin/indeed/glassdoor if the posting comes from one of them."""
    names = [item.get("job_publisher") or ""]
    names += [(o or {}).get("publisher") or "" for o in item.get("apply_options") or []]
    for name in names:
        for key in wanted:
            if key in name.lower():
                return key
    return None


def build_record(item, platform):
    url = item.get("job_apply_link") or ""
    for option in item.get("apply_options") or []:
        if platform in ((option or {}).get("publisher") or "").lower() and option.get("apply_link"):
            url = option["apply_link"]
            break
    title = item.get("job_title")
    if not url or not title:
        return None

    location = ", ".join(
        str(p) for p in (item.get("job_city"), item.get("job_state"), item.get("job_country")) if p
    ) or None

    types = item.get("job_employment_types") or [item.get("job_employment_type")]
    tags = [str(t).replace("_", " ").title() for t in types if t]
    if item.get("job_is_remote"):
        tags.append("Remote")

    posted = parse_date(item.get("job_posted_at_datetime_utc"))
    stable_id = item.get("job_id") or url
    return {
        "id": hashlib.md5(f"{platform}|{stable_id}".encode("utf-8")).hexdigest(),
        "source": platform,
        "title": title,
        "company": item.get("employer_name") or "Unknown",
        "location": location,
        "url": url,
        "posted_at": posted.isoformat() if posted else None,
        "description": item.get("job_description"),
        "tags": tags,
        "raw": {"job_id": item.get("job_id"), "publisher": item.get("job_publisher")},
    }


# --------------------------------------------------------------------- API
def api_get(session, params, retries=3):
    for attempt in range(retries):
        try:
            response = session.get(API_URL, params=params, timeout=TIMEOUT)
        except requests.RequestException as exc:
            if attempt == retries - 1:
                raise ApiStop(f"network error: {exc}")
            time.sleep(2 ** attempt)
            continue

        code = response.status_code
        if code in (401, 403):
            detail = response.text.strip().replace("\n", " ")[:200]
            raise ApiStop(f"API key rejected or not subscribed to JSearch (HTTP {code}): {detail}")
        if code == 429:
            if attempt == retries - 1:
                raise ApiStop("rate limit or monthly quota reached (HTTP 429)")
            time.sleep(2 ** attempt * 5)
            continue
        if code >= 500:
            time.sleep(2 ** attempt)
            continue
        response.raise_for_status()
        try:
            return response.json()
        except ValueError:
            return None
    return None


def fetch(api_key, queries, pages, date_posted, country, wanted, max_requests):
    session = requests.Session()
    session.headers.update({
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": API_HOST,
        "Accept": "application/json",
    })
    used = 0
    for query in queries:
        for page in range(1, pages + 1):
            if used >= max_requests:
                print(f"Request cap of {max_requests} reached; stopping.")
                return
            params = {"query": query, "page": page, "num_pages": 1, "date_posted": date_posted}
            if country:
                params["country"] = country
            data = api_get(session, params)  # may raise ApiStop
            used += 1
            payload = (data or {}).get("data") or {}
            items = payload.get("jobs", []) if isinstance(payload, dict) else payload
            kept = 0
            for item in items:
                platform = detect_platform(item, wanted)
                record = build_record(item, platform) if platform else None
                if record:
                    kept += 1
                    yield record
            print(f"'{query}' page {page}: {len(items)} results, {kept} from {', '.join(wanted)}")
            if not items:
                break
            time.sleep(0.5)


# -------------------------------------------------------------- jobs.json
def load_jobs(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return {j["id"]: j for j in data.get("jobs", []) if j.get("id")}
    except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError, AttributeError):
        return {}


def save_jobs(path, jobs):
    """Write atomically so a crash can never leave a half-written jobs.json."""
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(jobs),
        "jobs": list(jobs.values()),
    }
    folder = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=folder, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


# -------------------------------------------------------------------- main
def main():
    p = argparse.ArgumentParser(description="Collect LinkedIn, Indeed and Glassdoor jobs via JSearch.")
    p.add_argument("--out", default=os.path.join(BASE_DIR, "jobs.json"))
    p.add_argument("--queries", default=os.path.join(BASE_DIR, "common_platforms_queries.txt"))
    p.add_argument("--query", action="append", help="search text (repeatable); overrides the queries file")
    p.add_argument("--platforms", default=",".join(ALL_PLATFORMS), help="comma list: linkedin,indeed,glassdoor")
    p.add_argument("--pages", type=int, default=1, help="result pages per query (10 jobs each)")
    p.add_argument("--date-posted", default="3days", choices=["all", "today", "3days", "week", "month"])
    p.add_argument("--country", default="", help="optional country code, e.g. eg, us, gb, ae")
    p.add_argument("--max-requests", type=int, default=20, help="API calls allowed per run")
    p.add_argument("--dry-run", action="store_true", help="fetch and print counts, do not write jobs.json")
    args = p.parse_args()

    key = setting("JSEARCH_API_KEY")
    if not key:
        print("[error] JSEARCH_API_KEY is not set (environment or common_platforms.env)")
        return 2
    if looks_like_placeholder(key):
        print(f"[error] JSEARCH_API_KEY looks like a placeholder ('{key[:12]}...'), not a real key.\n"
              "        Get a real key: RapidAPI -> JSearch -> Pricing -> Subscribe (free Basic plan),\n"
              "        then copy the X-RapidAPI-Key value (about 50 characters) from the Playground tab\n"
              "        into common_platforms.env as:  JSEARCH_API_KEY=<the long key>")
        return 2

    wanted = tuple(x.strip().lower() for x in args.platforms.split(",") if x.strip() in ALL_PLATFORMS)
    if not wanted:
        p.error("--platforms must include linkedin, indeed and/or glassdoor")

    queries = args.query or load_queries(args.queries)
    jobs = load_jobs(args.out)
    added, updated = Counter(), Counter()
    exit_code = 0

    try:
        for record in fetch(key, queries, max(1, args.pages), args.date_posted,
                            args.country, wanted, max(1, args.max_requests)):
            bucket = updated if record["id"] in jobs else added
            bucket[record["source"]] += 1
            jobs[record["id"]] = record
    except ApiStop as exc:
        print(f"[stop] {exc}")
        exit_code = 2  # keep what we collected, but report failure

    if not args.dry_run:
        save_jobs(args.out, jobs)
    print(f"Done: {sum(added.values())} new {dict(added) or ''}, "
          f"{sum(updated.values())} refreshed. {len(jobs)} jobs total"
          f"{' (dry run, nothing saved)' if args.dry_run else f' in {args.out}'}.")
    return exit_code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as exc:
        print(f"[error] {exc}")
        sys.exit(1)