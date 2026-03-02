import argparse
import csv
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

DEFAULT_FACETS_LIST = (
    "LOCATIONS;WORK_LOCATIONS;WORKPLACE_TYPES;TITLES;CATEGORIES;"
    "ORGANIZATIONS;POSTING_DATES;FLEX_FIELDS"
)
DEFAULT_EXPAND_FIELDS = (
    "requisitionList.workLocation,"
    "requisitionList.otherWorkLocations,"
    "requisitionList.secondaryLocations,"
    "flexFieldsFacet.values,"
    "requisitionList.requisitionFlexFields"
)
DEFAULT_KEYWORDS = [
    "AI",
    "machine learning",
    "LLM",
    "generative AI",
    "data science",
    "NLP",
    "deep learning",
    "MLOps",
]

COMPANY_KEY_ALIASES = {
    "jpmorgan": "jpmorgan",
    "jpm": "jpmorgan",
    "jpmc": "jpmorgan",
    "oracle": "oracle",
}


@dataclass
class OracleHCMCrawlerConfig:
    company_name: str
    endpoint: str
    keywords: list[str]
    site_number: str | None = None
    location_id: str | None = None
    category_id: str | None = None
    page_size: int = 25
    facets_list: str = DEFAULT_FACETS_LIST
    expand_fields: str = DEFAULT_EXPAND_FIELDS
    sort_by: str = "RELEVANCY"
    request_timeout_seconds: int = 20
    retry_after_seconds: int = 15
    inter_page_sleep_seconds: float = 0.75
    inter_keyword_sleep_seconds: float = 1.5
    output_dir: str = "dataset"


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")

def canonical_company_key(company_name: str) -> str:
    name = company_name.lower()
    for alias, canonical in COMPANY_KEY_ALIASES.items():
        if alias in name:
            return canonical
    return slugify(company_name)


def get_origin(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def build_headers(config: OracleHCMCrawlerConfig) -> dict[str, str]:
    origin = get_origin(config.endpoint)
    referer_site = config.site_number or "CX_1001"
    referer = f"{origin}/hcmUI/CandidateExperience/en/sites/{referer_site}/jobs"
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": referer,
        "Origin": origin,
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }


def build_finder(config: OracleHCMCrawlerConfig, keyword: str, offset: int) -> str:
    parts = [
        f"siteNumber={config.site_number or ''}",
        f"facetsList={config.facets_list}",
        f"limit={config.page_size}",
        f"offset={offset}",
        f'keyword="{keyword}"',
        "lastSelectedFacet=CATEGORIES",
        f"sortBy={config.sort_by}",
    ]

    if config.location_id:
        parts.append(f"locationId={config.location_id}")
    if config.category_id:
        parts.append(f"selectedCategoriesFacet={config.category_id}")

    return "findReqs;" + ",".join(parts)


def build_apply_url(config: OracleHCMCrawlerConfig, job_id: Any) -> str:
    origin = get_origin(config.endpoint)
    if config.site_number:
        return (
            f"{origin}/hcmUI/CandidateExperience/en/sites/"
            f"{config.site_number}/job/{job_id}"
        )
    return ""


def extract_location_name(loc: Any) -> str:
    if isinstance(loc, dict):
        return str(loc.get("Name", ""))
    if isinstance(loc, list) and loc:
        first = loc[0]
        return str(first.get("Name", "")) if isinstance(first, dict) else str(first)
    return ""


def extract_location_list(locs: Any) -> list[str]:
    if not locs:
        return []
    if isinstance(locs, list):
        return [extract_location_name(loc) for loc in locs]
    return [extract_location_name(locs)]


def format_job(config: OracleHCMCrawlerConfig, job: dict[str, Any]) -> dict[str, Any]:
    flex_fields = job.get("requisitionFlexFields") or []
    flex = {
        field.get("FlexFieldNameCode"): field.get("FlexFieldValueCode")
        for field in flex_fields
        if isinstance(field, dict) and field.get("FlexFieldNameCode")
    }
    return {
        "id": job.get("Id"),
        "title": job.get("Title", ""),
        "primary_location": job.get("PrimaryLocation", ""),
        "work_location": extract_location_name(job.get("workLocation")),
        "other_locations": extract_location_list(job.get("otherWorkLocations")),
        "workplace_type": job.get("WorkplaceType", ""),
        "category": job.get("CategoryName", ""),
        "organization": job.get("OrganizationName", ""),
        "posted": job.get("PostedDate", ""),
        "flex_fields": flex,
        "apply_url": build_apply_url(config, job.get("Id")),
        "company": config.company_name,
        "source_endpoint": config.endpoint,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


def get_output_paths(config: OracleHCMCrawlerConfig) -> tuple[Path, Path]:
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    base = canonical_company_key(config.company_name)
    json_path = output_dir / f"{base}_jobs.json"
    csv_path = output_dir / f"{base}_jobs.csv"
    return json_path, csv_path


def load_existing(json_path: Path) -> dict[str, dict[str, Any]]:
    if not json_path.exists():
        return {}
    with json_path.open("r", encoding="utf-8") as file:
        jobs = json.load(file)
    return {str(job["id"]): job for job in jobs if isinstance(job, dict) and "id" in job}


def save_json(jobs_by_id: dict[str, dict[str, Any]], json_path: Path) -> None:
    with json_path.open("w", encoding="utf-8") as file:
        json.dump(list(jobs_by_id.values()), file, indent=2)


def save_csv(jobs_by_id: dict[str, dict[str, Any]], csv_path: Path) -> None:
    if not jobs_by_id:
        return

    rows = list(jobs_by_id.values())
    normalized_rows = []
    for row in rows:
        flat = dict(row)
        flat["other_locations"] = "; ".join(row.get("other_locations") or [])
        flat["flex_fields"] = json.dumps(row.get("flex_fields") or {})
        normalized_rows.append(flat)

    fields = list(normalized_rows[0].keys())
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(normalized_rows)


def persist(jobs_by_id: dict[str, dict[str, Any]], json_path: Path, csv_path: Path) -> None:
    save_json(jobs_by_id, json_path)
    save_csv(jobs_by_id, csv_path)


def fetch_page(
    config: OracleHCMCrawlerConfig,
    headers: dict[str, str],
    keyword: str,
    offset: int,
) -> list[dict[str, Any]] | None:
    params = {
        "onlyData": "true",
        "expand": config.expand_fields,
        "finder": build_finder(config, keyword, offset),
    }

    try:
        response = requests.get(
            config.endpoint,
            params=params,
            headers=headers,
            timeout=config.request_timeout_seconds,
        )
    except requests.RequestException as err:
        print(f"    [!] Network error: {err}")
        return None

    if response.status_code == 429:
        wait_seconds = int(response.headers.get("Retry-After", config.retry_after_seconds))
        print(f"    [!] Rate limited, waiting {wait_seconds}s")
        time.sleep(wait_seconds)
        return fetch_page(config, headers, keyword, offset)

    if response.status_code != 200:
        print(f"    [!] HTTP {response.status_code}: {response.text[:300]}")
        return None

    try:
        data = response.json()
        items = data.get("items", [])
        if not items:
            return []
        return items[0].get("requisitionList", [])
    except (ValueError, KeyError, IndexError, TypeError) as err:
        print(f"    [!] Parse error: {err}")
        return None


def crawl_keyword(
    config: OracleHCMCrawlerConfig,
    headers: dict[str, str],
    keyword: str,
    jobs_by_id: dict[str, dict[str, Any]],
    json_path: Path,
    csv_path: Path,
) -> dict[str, dict[str, Any]]:
    offset = 0
    page = 1
    new_count = 0

    print(f'\n  Searching: "{keyword}"')

    while True:
        print(f"    Page {page:>3} | offset {offset:>5} -> ", end="")
        requisitions = fetch_page(config, headers, keyword, offset)

        if requisitions is None:
            print("Error, skipping keyword.")
            break
        if not requisitions:
            print("No more results.")
            break

        new_on_page = 0
        for job in requisitions:
            job_id = str(job.get("Id", "")).strip()
            if job_id and job_id not in jobs_by_id:
                jobs_by_id[job_id] = format_job(config, job)
                new_on_page += 1

        new_count += new_on_page
        print(f"{new_on_page} new | total saved: {len(jobs_by_id)}")

        persist(jobs_by_id, json_path, csv_path)

        if len(requisitions) < config.page_size:
            print("    Last page reached.")
            break

        offset += config.page_size
        page += 1
        time.sleep(config.inter_page_sleep_seconds)

    print(f'  Done: "{keyword}" -> {new_count} new jobs added.')
    return jobs_by_id


def crawl_jobs(config: OracleHCMCrawlerConfig) -> dict[str, Any]:
    headers = build_headers(config)
    json_path, csv_path = get_output_paths(config)

    print("=" * 60)
    print(f"  {config.company_name} Jobs Crawler")
    print(f"  Endpoint : {config.endpoint}")
    print(f"  Started  : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    jobs_by_id = load_existing(json_path)
    if jobs_by_id:
        print(f"Resumed with {len(jobs_by_id)} previously saved jobs.")

    for keyword in config.keywords:
        jobs_by_id = crawl_keyword(
            config=config,
            headers=headers,
            keyword=keyword,
            jobs_by_id=jobs_by_id,
            json_path=json_path,
            csv_path=csv_path,
        )
        time.sleep(config.inter_keyword_sleep_seconds)

    persist(jobs_by_id, json_path, csv_path)

    print("\n" + "=" * 60)
    print(f"  TOTAL UNIQUE JOBS: {len(jobs_by_id)}")
    print(f"  JSON -> {json_path}")
    print(f"  CSV  -> {csv_path}")
    print("=" * 60)

    recent = sorted(jobs_by_id.values(), key=lambda item: item.get("posted", ""), reverse=True)[:20]
    if recent:
        print("\nMost Recent Listings")
        for job in recent:
            print(f"\n[{str(job.get('posted', ''))[:10]}] {job.get('title', '')}")
            print(f"  Location : {job.get('primary_location', '')}")
            print(f"  Apply    : {job.get('apply_url', '')}")

    return {
        "status": "success",
        "company_name": config.company_name,
        "jobs_count": len(jobs_by_id),
        "output_json": str(json_path),
        "output_csv": str(csv_path),
    }


def run_crawler(
    company_name: str,
    endpoint: str,
    keywords: list[str] | None = None,
    site_number: str | None = None,
    location_id: str | None = None,
    category_id: str | None = None,
    output_dir: str = "dataset",
) -> dict[str, Any]:
    config = OracleHCMCrawlerConfig(
        company_name=company_name,
        endpoint=endpoint,
        keywords=keywords or DEFAULT_KEYWORDS,
        site_number=site_number,
        location_id=location_id,
        category_id=category_id,
        output_dir=output_dir,
    )
    return crawl_jobs(config)


def parse_keywords(value: str | None) -> list[str]:
    if not value:
        return DEFAULT_KEYWORDS
    keywords = [item.strip() for item in value.split(",") if item.strip()]
    return keywords or DEFAULT_KEYWORDS


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generic Oracle HCM job crawler for similar career endpoints."
    )
    parser.add_argument("--company", required=True, help="Company display name")
    parser.add_argument("--endpoint", required=True, help="Recruiting API endpoint URL")
    parser.add_argument("--site-number", default=None, help="Site number (e.g., CX_1001)")
    parser.add_argument("--location-id", default=None, help="Optional location facet ID")
    parser.add_argument("--category-id", default=None, help="Optional category facet ID")
    parser.add_argument(
        "--keywords",
        default=None,
        help="Comma-separated keywords. Example: 'AI,LLM,Python'",
    )
    parser.add_argument("--output-dir", default="dataset", help="Output folder path")
    return parser


if __name__ == "__main__":
    cli = build_arg_parser().parse_args()
    result = run_crawler(
        company_name=cli.company,
        endpoint=cli.endpoint,
        keywords=parse_keywords(cli.keywords),
        site_number=cli.site_number,
        location_id=cli.location_id,
        category_id=cli.category_id,
        output_dir=cli.output_dir,
    )

    if result.get("status") != "success":
        raise SystemExit(1)
