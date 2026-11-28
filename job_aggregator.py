"""
Job aggregator: collects public job postings, normalizes them, deduplicates
them, and saves them to JSON.

Run once:
    python job_aggregator.py

Run every hour:
    python job_aggregator.py --loop 3600

Include TheMuse (currently returns HTTP 404):
    python job_aggregator.py --include-themuse

Limit EPAM pages (default 100):
    python job_aggregator.py --epam-limit 200

Process all collected EPAM vacancies:
    python job_aggregator.py --epam-limit 0

Dependencies:
    pip install requests playwright
    playwright install chromium
"""

import argparse
import hashlib
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests


SINCE = datetime(2020, 1, 1, tzinfo=timezone.utc)
HEADERS = {
    "User-Agent": "JobAggregator/1.0 (job aggregation script)"
}
REQUEST_TIMEOUT = 20
EPAM_WORKERS = 10
SMARTRECRUITERS_API = "https://api.smartrecruiters.com/v1/companies"
SMARTRECRUITERS_WORKERS = 5
DATE_UNTIL = datetime.now(timezone.utc)


def get(url, params=None, retries=5):
    """GET JSON with exponential backoff and Retry-After support."""
    for attempt in range(retries):
        try:
            response = requests.get(
                url,
                params=params,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
            )

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                try:
                    wait = int(retry_after) if retry_after else 2 ** attempt * 5
                except ValueError:
                    try:
                        wait = max(
                            1,
                            int(
                                (
                                    parsedate_to_datetime(retry_after)
                                    - datetime.now(timezone.utc)
                                ).total_seconds()
                            ),
                        )
                    except (TypeError, ValueError, OverflowError):
                        wait = 2 ** attempt * 5

                print(f"[warn] Rate limited by {url}; waiting {wait}s")
                time.sleep(wait)
                continue

            response.raise_for_status()
            return response.json()

        except requests.HTTPError as exc:
            print(f"[warn] {url}: {exc}")
            if exc.response is not None and exc.response.status_code < 500:
                return None
            if attempt < retries - 1:
                time.sleep(2 ** attempt)

        except (requests.RequestException, ValueError) as exc:
            print(f"[warn] {url}: {exc}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)

    return None


def parse_date(value):
    """Parse common date formats and always return a UTC-aware datetime."""
    if value is None or value == "":
        return None

    try:
        if isinstance(value, datetime):
            dt = value
        elif isinstance(value, (int, float)):
            # Handle Unix timestamps in seconds and milliseconds.
            timestamp = value / 1000 if value > 10_000_000_000 else value
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        else:
            text = str(value).strip()
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            dt = datetime.fromisoformat(text)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    except (ValueError, TypeError, OverflowError, OSError):
        return None


def within_date_window(value):
    """Return whether a known posting date is within the configured UTC window.

    Unknown dates are retained, but must not be represented as confirmed to
    fall within the window.
    """
    posted = parse_date(value)
    return posted is None or SINCE <= posted <= DATE_UNTIL


def job(source, title, company, location, url, posted, description,
        tags=None, raw=None):
    """Normalize a job record."""
    title = title or "Untitled"
    company = company or "Unknown"
    url = url or ""

    return {
        "id": hashlib.md5(
            f"{company}|{title}|{url}".encode("utf-8")
        ).hexdigest(),
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

    for item in data.get("jobs", []):
        try:
            yield job(
                "remotive",
                item.get("title"),
                item.get("company_name"),
                item.get("candidate_required_location"),
                item.get("url"),
                parse_date(item.get("publication_date")),
                item.get("description"),
                item.get("tags"),
                item,
            )
        except (KeyError, TypeError) as exc:
            print(f"[warn] Skipping malformed Remotive job: {exc}")


def fetch_arbeitnow():
    page = 1

    while page <= 50:
        data = get(
            "https://www.arbeitnow.com/api/job-board-api",
            {"page": page},
        )

        if not data or not data.get("data"):
            break

        for item in data["data"]:
            try:
                yield job(
                    "arbeitnow",
                    item.get("title"),
                    item.get("company_name"),
                    item.get("location"),
                    item.get("url"),
                    parse_date(item.get("created_at")),
                    item.get("description"),
                    item.get("tags"),
                    item,
                )
            except (KeyError, TypeError) as exc:
                print(f"[warn] Skipping malformed Arbeitnow job: {exc}")

        page += 1
        time.sleep(1)


def fetch_remoteok():
    data = get("https://remoteok.com/api") or []

    # The first item is Remote OK's legal notice, not a job.
    for item in data[1:]:
        try:
            yield job(
                "remoteok",
                item.get("position"),
                item.get("company"),
                item.get("location"),
                item.get("url"),
                parse_date(item.get("date")),
                item.get("description"),
                item.get("tags"),
                item,
            )
        except (KeyError, TypeError) as exc:
            print(f"[warn] Skipping malformed Remote OK job: {exc}")


def fetch_indeed_authorized_export(path):
    """Normalize jobs from a user-provided authorized Indeed API/export JSON.

    This adapter does not make network requests or scrape Indeed pages. The
    caller is responsible for supplying data obtained under an approved
    Indeed integration and respecting its retention/display requirements.
    """
    from bs4 import BeautifulSoup

    with open(path, encoding="utf-8") as file:
        payload = json.load(file)
    records = payload if isinstance(payload, list) else payload.get("jobs", [])
    if not isinstance(records, list):
        raise ValueError("Indeed export must be a JSON list or contain a jobs list")

    for item in records:
        if not isinstance(item, dict):
            continue
        description = item.get("description") or item.get("jobDescription") or ""
        description_text = BeautifulSoup(str(description), "html.parser").get_text(
            " ", strip=True
        )
        tags = item.get("tags") or item.get("attributes") or []
        if isinstance(tags, str):
            tags = [tags]
        yield job(
            "indeed",
            item.get("title") or item.get("jobTitle"),
            item.get("company") or item.get("companyName"),
            item.get("location") or item.get("jobLocation"),
            item.get("url") or item.get("jobUrl") or item.get("viewJobUrl"),
            parse_date(item.get("posted_at") or item.get("datePosted") or item.get("date")),
            description_text,
            tags,
            item,
        )


def fetch_themuse():
    """
    TheMuse fetcher is retained.

    Its former public endpoint currently returns HTTP 404. This function
    remains available and can be enabled with --include-themuse if the
    endpoint becomes available again.
    """
    page = 0

    while page < 100:
        data = get(
            "https://www.themuse.com/api/public/jobs",
            {"page": page},
        )

        if not data or not data.get("results"):
            break

        for item in data["results"]:
            try:
                locations = ", ".join(
                    loc.get("name", "")
                    for loc in item.get("locations", [])
                    if loc.get("name")
                )
                company_data = item.get("company") or {}
                refs = item.get("refs") or {}

                yield job(
                    "themuse",
                    item.get("name"),
                    company_data.get("name"),
                    locations,
                    refs.get("landing_page"),
                    parse_date(item.get("publication_date")),
                    item.get("contents"),
                    [
                        category.get("name")
                        for category in item.get("categories", [])
                        if category.get("name")
                    ],
                    item,
                )
            except (AttributeError, TypeError) as exc:
                print(f"[warn] Skipping malformed TheMuse job: {exc}")

        if page >= data.get("page_count", 0) - 1:
            break

        page += 1
        time.sleep(1)



def load_smartrecruiters_companies(cli_value=None, file_path="smartrecruiters_companies.txt"):
    """Load company identifiers from CLI and/or a newline-separated text file.

    Identifiers are the company slug in URLs such as
    https://jobs.smartrecruiters.com/COMPANY/...
    """
    companies = []
    if cli_value:
        companies.extend(part.strip() for part in cli_value.split(","))

    try:
        with open(file_path, encoding="utf-8") as file:
            companies.extend(
                line.strip() for line in file
                if line.strip() and not line.lstrip().startswith("#")
            )
    except FileNotFoundError:
        pass

    # Accept pasted career-site/job URLs as well as plain company identifiers.
    normalized = []
    for company in companies:
        company = company.strip().strip("/")
        if not company:
            continue
        if "smartrecruiters.com/" in company:
            company = company.split("smartrecruiters.com/", 1)[1].split("/", 1)[0]
        company = company.split("?", 1)[0].strip()
        if company and company not in normalized:
            normalized.append(company)
    return normalized


def smartrecruiters_location(location_data):
    if not isinstance(location_data, dict):
        return None
    parts = [
        location_data.get("city"),
        location_data.get("region"),
        location_data.get("country"),
    ]
    return ", ".join(str(part) for part in parts if part) or None


def fetch_smartrecruiters(companies, max_per_company=0, workers=SMARTRECRUITERS_WORKERS):
    """Fetch currently active public jobs for each configured company.

    SmartRecruiters exposes postings per company, not a global all-company feed.
    max_per_company=0 means paginate through every active posting for that company.
    Details are checked for active status and an application URL before yielding.
    """
    if not companies:
        print("[skip] SmartRecruiters: no company identifiers configured")
        print("       Add slugs/URLs to smartrecruiters_companies.txt or use --smartrecruiters-companies")
        return

    session = requests.Session()
    session.headers.update(HEADERS)

    def fetch_company(company):
        offset = 0
        limit = 100
        collected = []
        while True:
            endpoint = f"{SMARTRECRUITERS_API}/{company}/postings"
            try:
                response = session.get(
                    endpoint,
                    params={"limit": limit, "offset": offset, "destination": "PUBLIC"},
                    timeout=REQUEST_TIMEOUT,
                )
                if response.status_code == 404:
                    print(f"\n[warn] SmartRecruiters company not found or feed disabled: {company}")
                    break
                response.raise_for_status()
                payload = response.json()
            except (requests.RequestException, ValueError) as exc:
                print(f"\n[warn] SmartRecruiters {company}: {exc}")
                break

            postings = payload.get("content", []) if isinstance(payload, dict) else []
            if not postings:
                break

            collected.extend(postings)
            offset += len(postings)
            total = payload.get("totalFound")
            if len(postings) < limit or (total is not None and offset >= int(total)):
                break
            if max_per_company and len(collected) >= max_per_company:
                collected = collected[:max_per_company]
                break
            time.sleep(0.2)

        if max_per_company:
            collected = collected[:max_per_company]
        return company, collected

    all_postings = []
    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(companies)))) as executor:
        futures = {executor.submit(fetch_company, company): company for company in companies}
        for future in as_completed(futures):
            try:
                company, postings = future.result()
                print(f"SmartRecruiters [{company}]: {len(postings)} active postings found")
                for posting in postings:
                    posting["_company_identifier"] = company
                    all_postings.append(posting)
            except Exception as exc:
                print(f"\n[warn] SmartRecruiters company fetch failed: {exc}")

    def fetch_details(posting):
        company = posting.get("_company_identifier")
        posting_id = posting.get("id") or posting.get("uuid")
        if not company or not posting_id:
            return None
        url = f"{SMARTRECRUITERS_API}/{company}/postings/{posting_id}"
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            details = response.json()
        except (requests.RequestException, ValueError) as exc:
            print(f"\n[warn] SmartRecruiters detail {company}/{posting_id}: {exc}")
            return None

        # The detail endpoint exposes active and applyUrl fields. Do not label
        # an expired/unavailable posting as applicable.
        if details.get("active") is False:
            return None
        apply_url = details.get("applyUrl")
        if not apply_url:
            return None

        released = parse_date(
            details.get("releasedDate") or posting.get("releasedDate")
        )
        if released is None or released < SINCE or released > DATE_UNTIL:
            return None

        company_data = details.get("company") or posting.get("company") or {}
        job_ad = details.get("jobAd") or {}
        sections = job_ad.get("sections") or {}
        description_parts = []
        for section_name in ("jobDescription", "qualifications", "additionalInformation"):
            section = sections.get(section_name) or {}
            if section.get("text"):
                description_parts.append(section["text"])
        description = "\n\n".join(description_parts) or None

        location = smartrecruiters_location(
            details.get("location") or posting.get("location")
        )
        tags = []
        for field in ("industry", "function", "department", "experienceLevel", "typeOfEmployment"):
            value = details.get(field) or posting.get(field)
            if isinstance(value, dict) and value.get("label"):
                tags.append(value["label"])

        record = job(
            "smartrecruiters",
            details.get("name") or posting.get("name"),
            company_data.get("name") or company,
            location,
            apply_url,
            released,
            description,
            tags,
            details,
        )
        # Preserve the employer's public job page separately from the apply URL.
        record["job_page"] = (
            f"https://jobs.smartrecruiters.com/{company}/{posting_id}"
        )
        record["application_status"] = "active_at_fetch_time"
        return record

    total = len(all_postings)
    print(f"SmartRecruiters: checking application links for {total} postings")
    completed = 0
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = [executor.submit(fetch_details, item) for item in all_postings]
        for future in as_completed(futures):
            completed += 1
            try:
                record = future.result()
                if record:
                    yield record
            except Exception as exc:
                print(f"\n[warn] SmartRecruiters detail processing: {exc}")
            print(f"\rSmartRecruiters detail progress: {completed}/{total}", end="", flush=True)
    if total:
        print()


EPAM_LIST = "https://careers.epam.com/en/jobs"


def get_text(url, retries=3):
    """GET an HTML page with retries."""
    for attempt in range(retries):
        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
            )

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                try:
                    wait = int(retry_after) if retry_after else 2 ** attempt * 5
                except ValueError:
                    wait = 2 ** attempt * 5
                time.sleep(wait)
                continue

            response.raise_for_status()
            return response.text

        except requests.RequestException as exc:
            print(f"\n[warn] {url}: {exc}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)

    return None


def epam_collect_links(max_clicks=200):
    """
    Render EPAM's JavaScript listing page and collect vacancy URLs.
    Requires Playwright and Chromium.
    """
    from playwright.sync_api import sync_playwright

    links = set()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(user_agent=HEADERS["User-Agent"])

        try:
            page.goto(
                EPAM_LIST,
                wait_until="domcontentloaded",
                timeout=60000,
            )
            page.wait_for_timeout(3000)

            for _ in range(max_clicks):
                before = len(links)

                for anchor in page.query_selector_all("a[href*='/vacancy/']"):
                    href = anchor.get_attribute("href")
                    if href:
                        links.add(
                            requests.compat.urljoin(
                                EPAM_LIST,
                                href.split("?")[0],
                            )
                        )

                next_button = page.query_selector(
                    "button:has-text('Load more'), "
                    "button:has-text('Show more'), "
                    "[aria-label*='Next' i]:not([disabled])"
                )

                if (
                    next_button is None
                    or not next_button.is_enabled()
                ):
                    break

                next_button.click()
                page.wait_for_timeout(1500)

                if len(links) == before and not next_button.is_visible():
                    break

        finally:
            browser.close()

    return sorted(links)


def epam_parse_vacancy(url, html):
    """Extract structured JobPosting data from an EPAM vacancy page."""
    if not html or "no longer available" in html.lower():
        return None

    structured_data = None

    # Find JSON-LD script blocks, including application/ld+json.
    script_pattern = (
        r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>'
        r'(.*?)</script>'
    )

    for block in re.findall(script_pattern, html, flags=re.IGNORECASE | re.DOTALL):
        try:
            data = json.loads(block.strip())
        except json.JSONDecodeError:
            continue

        items = data if isinstance(data, list) else [data]

        for item in items:
            if not isinstance(item, dict):
                continue

            if item.get("@type") == "JobPosting":
                structured_data = item
                break

        if structured_data:
            break

    if structured_data:
        location_data = structured_data.get("jobLocation")
        if isinstance(location_data, list):
            location_data = location_data[0] if location_data else None

        address = (
            location_data.get("address", {})
            if isinstance(location_data, dict)
            else {}
        )

        if isinstance(address, dict):
            locality = address.get("addressLocality")
            country = address.get("addressCountry")

            if isinstance(country, dict):
                country = country.get("name")

            location = ", ".join(
                str(part)
                for part in (locality, country)
                if part
            )
        else:
            location = None

        return job(
            "epam",
            structured_data.get("title"),
            "EPAM",
            location,
            url,
            parse_date(structured_data.get("datePosted")),
            structured_data.get("description"),
            [],
            structured_data,
        )

    # Fallback: extract the page's H1 title if JSON-LD is unavailable.
    match = re.search(
        r"<h1\b[^>]*>(.*?)</h1>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    title = re.sub(r"<[^>]+>", "", match.group(1)).strip() if match else url

    return job("epam", title, "EPAM", None, url, None, None)


def fetch_epam(max_vacancies=100, workers=EPAM_WORKERS, known_urls=None):
    """
    Fetch EPAM vacancy pages concurrently.

    max_vacancies=0 means process every collected vacancy.
    """
    try:
        links = epam_collect_links()
    except ImportError:
        print(
            "[skip] EPAM: install Playwright with "
            "'pip install playwright && playwright install chromium'"
        )
        return
    except Exception as exc:
        print(f"[error] EPAM link collection failed: {exc}")
        return

    if known_urls:
        before = len(links)
        links = [u for u in links if u not in known_urls]
        print(f"epam: {before - len(links)} already stored, skipping them")

    if max_vacancies > 0:
        links = links[:max_vacancies]

    total = len(links)
    print(f"epam: processing {total} vacancies using {workers} workers")

    if not links:
        return

    completed = 0

    # Concurrent requests avoid waiting for every page one by one.
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        future_to_url = {
            executor.submit(get_text, url): url
            for url in links
        }

        for future in as_completed(future_to_url):
            url = future_to_url[future]
            completed += 1

            try:
                html = future.result()
                if html:
                    parsed_job = epam_parse_vacancy(url, html)
                    if parsed_job:
                        yield parsed_job
            except Exception as exc:
                print(f"\n[warn] EPAM parsing failed for {url}: {exc}")

            print(
                f"\rEPAM progress: {completed}/{total}",
                end="",
                flush=True,
            )

    print()


def run(out="jobs.json", include_themuse=False, epam_limit=100,
        smartrecruiters_companies=None, smartrecruiters_limit=0,
        selected_sources=None, indeed_json=None):
    """Run selected sources, merge with existing jobs, and save JSON."""
    try:
        with open(out, encoding="utf-8") as file:
            previous_data = json.load(file)
            jobs = {
                item["id"]: item
                for item in previous_data.get("jobs", [])
                if item.get("id")
                and within_date_window(item.get("posted_at"))
            }
    except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError):
        jobs = {}

    if selected_sources is None:
        selected_sources = {"remotive", "arbeitnow", "remoteok", "epam"}
    else:
        selected_sources = set(selected_sources)
    if include_themuse:
        selected_sources.add("themuse")
    available = {
        "remotive": fetch_remotive,
        "arbeitnow": fetch_arbeitnow,
        "remoteok": fetch_remoteok,
    }
    if include_themuse or "themuse" in selected_sources:
        available["themuse"] = fetch_themuse
    if smartrecruiters_companies:
        available["smartrecruiters"] = lambda: fetch_smartrecruiters(
            smartrecruiters_companies,
            max_per_company=smartrecruiters_limit,
        )
    if indeed_json:
        available["indeed"] = lambda: fetch_indeed_authorized_export(indeed_json)
    known_epam = {
        item.get("url") for item in jobs.values() if item.get("source") == "epam"
    }
    available["epam"] = lambda: fetch_epam(
        max_vacancies=epam_limit, known_urls=known_epam
    )
    unknown = selected_sources - available.keys()
    if unknown:
        raise ValueError(
            "Unavailable or unconfigured source(s): " + ", ".join(sorted(unknown))
        )
    sources = [available[name] for name in sorted(selected_sources)]

    for fetcher in sources:
        source_name = getattr(fetcher, "__name__", "fetch_epam")
        if source_name == "<lambda>":
            source_name = "fetch_epam"

        count = 0

        try:
            for item in fetcher():
                if not within_date_window(item.get("posted_at")):
                    continue

                jobs[item["id"]] = item
                count += 1

        except Exception as exc:
            print(f"\n[error] {source_name}: {exc}")

        print(f"{source_name}: {count} jobs")

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(jobs),
        "jobs": list(jobs.values()),
    }

    with open(out, "w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)

    print(f"Saved {len(jobs)} jobs to {out}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Collect and normalize job postings."
    )
    parser.add_argument(
        "--sources",
        default="remotive,arbeitnow,remoteok,epam",
        help="Comma-separated sources to run: remotive,arbeitnow,remoteok,epam,themuse,smartrecruiters,indeed.",
    )
    parser.add_argument(
        "--indeed-json",
        default="",
        help="Path to a JSON export from an authorized Indeed API/integration; this does not scrape Indeed pages.",
    )
    parser.add_argument(
        "--loop",
        type=int,
        default=0,
        help="Repeat every N seconds (example: --loop 3600).",
    )
    parser.add_argument(
        "--out",
        default="jobs.json",
        help="Output JSON filename.",
    )
    parser.add_argument(
        "--include-themuse",
        action="store_true",
        help="Enable TheMuse fetcher (its endpoint may return 404).",
    )
    parser.add_argument(
        "--smartrecruiters-companies",
        default="",
        help="Comma-separated SmartRecruiters company slugs or job/career URLs. Also reads smartrecruiters_companies.txt.",
    )
    parser.add_argument(
        "--smartrecruiters-limit",
        type=int,
        default=0,
        help="Maximum active postings per SmartRecruiters company; 0 means all pages.",
    )
    parser.add_argument(
        "--epam-limit",
        type=int,
        default=100,
        help="Maximum EPAM vacancies to process; use 0 for all.",
    )

    args = parser.parse_args()

    if args.loop < 0:
        parser.error("--loop must be zero or a positive number.")
    if args.epam_limit < 0:
        parser.error("--epam-limit must be zero or a positive number.")
    if args.smartrecruiters_limit < 0:
        parser.error("--smartrecruiters-limit must be zero or a positive number.")

    selected_sources = {
        source.strip().lower()
        for source in args.sources.split(",")
        if source.strip()
    }

    # SmartRecruiters is handled by run_smartrecruiters.py (skips known jobs)
    smartrecruiters_companies = (
        load_smartrecruiters_companies(args.smartrecruiters_companies)
        if args.smartrecruiters_companies else []
    )

    while True:
        run(
            out=args.out,
            include_themuse=args.include_themuse,
            epam_limit=args.epam_limit,
            smartrecruiters_companies=smartrecruiters_companies,
            smartrecruiters_limit=args.smartrecruiters_limit,
            selected_sources=selected_sources,
            indeed_json=args.indeed_json or None,
        )

        if not args.loop:
            break

        print(f"\nNext run in {args.loop} seconds.")
        time.sleep(args.loop)
