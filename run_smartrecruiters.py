"""
Collect jobs only from SmartRecruiters and merge them into jobs.json.

Postings already stored in jobs.json are skipped BEFORE their detail page is
requested, so a daily run only fetches what is new.

    python run_smartrecruiters.py              # all configured companies
    python run_smartrecruiters.py --limit 20   # quick test
"""
import argparse
import json
import os
import re
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import requests

from job_aggregator import (
    DATE_UNTIL,
    HEADERS,
    REQUEST_TIMEOUT,
    SINCE,
    SMARTRECRUITERS_API,
    job,
    load_smartrecruiters_companies,
    parse_date,
    smartrecruiters_location,
)

WORKERS = 5
PAGE_SIZE = 100
PAGE_RE = re.compile(r"smartrecruiters\.com/([^/]+)/([^/?#]+)")


def request_json(session, url, params=None, retries=4):
    """GET JSON with backoff. Returns None on 404 or after repeated failures."""
    for attempt in range(retries):
        try:
            response = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
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
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            if attempt == retries - 1:
                print(f"[warn] {url}: {exc}")
            else:
                time.sleep(2 ** attempt)
    return None


def load_jobs(path):
    try:
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
        return {j["id"]: j for j in data.get("jobs", []) if j.get("id")}
    except (FileNotFoundError, json.JSONDecodeError, TypeError, AttributeError):
        return {}


def save_jobs(path, jobs):
    """Atomic write: a crash can never leave a half-written jobs.json."""
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(jobs),
        "jobs": list(jobs.values()),
    }
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def known_keys(jobs):
    """Set of 'company/postingId' for every SmartRecruiters job already stored."""
    keys = set()
    for item in jobs.values():
        if item.get("source") != "smartrecruiters":
            continue
        match = PAGE_RE.search(item.get("job_page") or "")
        if match:
            keys.add(f"{match.group(1)}/{match.group(2)}")
    return keys


def list_postings(session, company, limit):
    """Return every active posting of a company, or None if the listing failed."""
    collected = []
    offset = 0
    while True:
        payload = request_json(
            session,
            f"{SMARTRECRUITERS_API}/{company}/postings",
            {"limit": PAGE_SIZE, "offset": offset, "destination": "PUBLIC"},
        )
        if not isinstance(payload, dict):
            return None if offset == 0 else collected
        postings = payload.get("content") or []
        if not postings:
            break
        collected.extend(postings)
        offset += len(postings)
        total = payload.get("totalFound")
        if len(postings) < PAGE_SIZE or (total is not None and offset >= int(total)):
            break
        if limit and len(collected) >= limit:
            break
        time.sleep(0.2)
    return collected[:limit] if limit else collected


def build_record(session, company, posting):
    posting_id = posting.get("id") or posting.get("uuid")
    if not posting_id:
        return None

    details = request_json(session, f"{SMARTRECRUITERS_API}/{company}/postings/{posting_id}")
    if not details or details.get("active") is False:
        return None

    apply_url = details.get("applyUrl")
    if not apply_url:
        return None

    released = parse_date(details.get("releasedDate") or posting.get("releasedDate"))
    if released is None or released < SINCE or released > DATE_UNTIL:
        return None

    company_data = details.get("company") or posting.get("company") or {}
    sections = ((details.get("jobAd") or {}).get("sections")) or {}
    description = "\n\n".join(
        sections[name]["text"]
        for name in ("jobDescription", "qualifications", "additionalInformation")
        if (sections.get(name) or {}).get("text")
    ) or None

    tags = []
    for field in ("industry", "function", "department", "experienceLevel", "typeOfEmployment"):
        value = details.get(field) or posting.get(field)
        if isinstance(value, dict) and value.get("label"):
            tags.append(value["label"])

    record = job(
        "smartrecruiters",
        details.get("name") or posting.get("name"),
        company_data.get("name") or company,
        smartrecruiters_location(details.get("location") or posting.get("location")),
        apply_url,
        released,
        description,
        tags,
        details,
    )
    record["job_page"] = f"https://jobs.smartrecruiters.com/{company}/{posting_id}"
    record["application_status"] = "active_at_fetch_time"
    return record


def main():
    parser = argparse.ArgumentParser(description="Collect SmartRecruiters jobs.")
    parser.add_argument("--companies", default="", help="extra slugs/URLs, comma-separated")
    parser.add_argument("--limit", type=int, default=0, help="max postings per company (0 = all)")
    parser.add_argument("--out", default="jobs.json")
    args = parser.parse_args()

    companies = load_smartrecruiters_companies(args.companies)
    if not companies:
        print("No companies configured. Fill smartrecruiters_companies.txt first.")
        return

    jobs = load_jobs(args.out)
    known = known_keys(jobs)
    print(f"SmartRecruiters: {len(companies)} companies, {len(known)} postings already stored")

    session = requests.Session()
    session.headers.update(HEADERS)
    added = skipped = 0

    for company in companies:
        postings = list_postings(session, company, args.limit)
        if postings is None:
            print(f"[warn] {company}: not found, disabled or unreachable; skipped")
            continue

        fresh = [
            p for p in postings
            if f"{company}/{p.get('id') or p.get('uuid')}" not in known
        ]
        skipped += len(postings) - len(fresh)
        print(f"{company}: {len(postings)} active, {len(fresh)} new")

        if fresh:
            with ThreadPoolExecutor(max_workers=WORKERS) as executor:
                futures = [executor.submit(build_record, session, company, p) for p in fresh]
                for future in as_completed(futures):
                    try:
                        record = future.result()
                    except Exception as exc:
                        print(f"[warn] {company}: {exc}")
                        continue
                    if record:
                        jobs[record["id"]] = record
                        added += 1
            save_jobs(args.out, jobs)  # save after every company

    save_jobs(args.out, jobs)
    print(f"Done: {added} new jobs added, {skipped} already known and skipped. "
          f"{len(jobs)} jobs in {args.out}")


if __name__ == "__main__":
    main()
