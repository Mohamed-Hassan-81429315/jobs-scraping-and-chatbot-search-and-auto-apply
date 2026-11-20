"""
Job aggregator: pulls postings from public, no-auth job APIs,
normalizes them to one schema, dedupes, and writes JSON.
Run once:      python job_aggregator.py
Run as service: python job_aggregator.py --loop 3600   (every hour)

pip install requests
"""
import argparse
import json
import time
import hashlib
from datetime import datetime, timezone

import requests

SINCE = datetime(2019, 1, 1, tzinfo=timezone.utc)  # keep only jobs on/after this date
HEADERS = {"User-Agent": "JobAggregator/1.0 (contact: you@example.com)"}


def get(url, params=None, retries=5):
    """GET with exponential backoff; honors Retry-After (polite, not a bypass)."""
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=30)
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 2 ** attempt * 5))
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            print(f"[warn] {url}: {e}")
            time.sleep(2 ** attempt)
    return None


def parse_date(value):
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def job(source, title, company, location, url, posted, description, tags=None, raw=None):
    return {
        "id": hashlib.md5(f"{company}|{title}|{url}".encode()).hexdigest(),
        "source": source,
        "title": title,
        "company": company,
        "location": location,
        "url": url,
        "posted_at": posted.isoformat() if posted else None,
        "description": description,
        "tags": tags or [],
        "raw": raw,
    }


def fetch_remotive():
    data = get("https://remotive.com/api/remote-jobs") or {}
    for j in data.get("jobs", []):
        yield job("remotive", j["title"], j["company_name"],
                  j.get("candidate_required_location"), j["url"],
                  parse_date(j.get("publication_date")), j.get("description"),
                  j.get("tags"), j)


def fetch_arbeitnow():
    page = 1
    while page <= 50:
        data = get("https://www.arbeitnow.com/api/job-board-api", {"page": page})
        if not data or not data.get("data"):
            break
        for j in data["data"]:
            yield job("arbeitnow", j["title"], j["company_name"], j.get("location"),
                      j["url"], parse_date(j.get("created_at")), j.get("description"),
                      j.get("tags"), j)
        page += 1
        time.sleep(1)


def fetch_remoteok():
    data = get("https://remoteok.com/api") or []
    for j in data[1:]:  # first item is legal notice
        yield job("remoteok", j.get("position"), j.get("company"), j.get("location"),
                  j.get("url"), parse_date(j.get("date")), j.get("description"),
                  j.get("tags"), j)


def fetch_themuse():
    page = 0
    while page < 100:
        data = get("https://www.themuse.com/api/public/jobs", {"page": page})
        if not data or not data.get("results"):
            break
        for j in data["results"]:
            locs = ", ".join(l["name"] for l in j.get("locations", []))
            yield job("themuse", j["name"], j["company"]["name"], locs,
                      j["refs"]["landing_page"], parse_date(j.get("publication_date")),
                      j.get("contents"), [c["name"] for c in j.get("categories", [])], j)
        if page >= data.get("page_count", 0) - 1:
            break
        page += 1
        time.sleep(1)


EPAM_LIST = "https://careers.epam.com/en/jobs"


def get_text(url, retries=3):
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 429:
                time.sleep(int(r.headers.get("Retry-After", 2 ** attempt * 5)))
                continue
            r.raise_for_status()
            return r.text
        except requests.RequestException as e:
            print(f"[warn] {url}: {e}")
            time.sleep(2 ** attempt)
    return None


def epam_collect_links(max_clicks=200):
    """Render the JS listing page and collect vacancy URLs (pip install playwright;
    playwright install chromium). Selectors below may need adjusting if EPAM
    changes its markup."""
    from playwright.sync_api import sync_playwright
    links = set()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=HEADERS["User-Agent"])
        page.goto(EPAM_LIST, wait_until="networkidle")
        for _ in range(max_clicks):
            before = len(links)
            for a in page.query_selector_all("a[href*='/vacancy/']"):
                href = a.get_attribute("href")
                if href:
                    links.add(requests.compat.urljoin(EPAM_LIST, href.split("?")[0]))
            nxt = page.query_selector(
                "button:has-text('Load more'), button:has-text('Show more'), "
                "[aria-label*='Next' i]:not([disabled])")
            if nxt is None or not nxt.is_enabled():
                break
            nxt.click()
            page.wait_for_load_state("networkidle")
            time.sleep(1)  # be polite
            if len(links) == before and nxt.is_visible() is False:
                break
        browser.close()
    return sorted(links)


def epam_parse_vacancy(url, html):
    import re
    if "no longer available" in html.lower():
        return None
    ld = None
    for block in re.findall(
            r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html, re.S):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        for item in (data if isinstance(data, list) else [data]):
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                ld = item
    if ld:
        loc = ld.get("jobLocation")
        loc = loc[0] if isinstance(loc, list) and loc else loc
        addr = (loc or {}).get("address", {}) if isinstance(loc, dict) else {}
        location = ", ".join(filter(None, [addr.get("addressLocality"),
                                           addr.get("addressCountry")
                                           if isinstance(addr.get("addressCountry"), str) else None]))
        return job("epam", ld.get("title"), "EPAM", location, url,
                   parse_date(ld.get("datePosted")), ld.get("description"),
                   [], ld)
    # Fallback: page title only
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    title = re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else url
    return job("epam", title, "EPAM", None, url, None, None)


def fetch_epam():
    try:
        links = epam_collect_links()
    except ImportError:
        print("[skip] epam: run `pip install playwright && playwright install chromium`")
        return
    print(f"epam: {len(links)} vacancy links found")
    for url in links:
        html = get_text(url)
        if html:
            j = epam_parse_vacancy(url, html)
            if j:
                yield j
        time.sleep(1)


SOURCES = [fetch_remotive, fetch_arbeitnow, fetch_remoteok, fetch_themuse, fetch_epam]
# To add more: Adzuna / Jooble / USAJobs offer free API keys -> add a fetcher each.


def run(out="jobs.json"):
    # load previous run so history accumulates over time
    try:
        with open(out, encoding="utf-8") as f:
            jobs = {j["id"]: j for j in json.load(f)["jobs"]}
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        jobs = {}

    for fetcher in SOURCES:
        count = 0
        try:
            for j in fetcher():
                posted = parse_date(j["posted_at"])
                if posted and posted < SINCE:
                    continue
                jobs[j["id"]] = j
                count += 1
        except Exception as e:  # one failing source must not stop the others
            print(f"[error] {fetcher.__name__}: {e}")
        print(f"{fetcher.__name__}: {count} jobs")

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(jobs),
        "jobs": list(jobs.values()),
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(jobs)} jobs to {out}")
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--loop", type=int, default=0, help="repeat every N seconds")
    ap.add_argument("--out", default="jobs.json")
    args = ap.parse_args()
    while True:
        run(args.out)
        if not args.loop:
            break
        time.sleep(args.loop)
