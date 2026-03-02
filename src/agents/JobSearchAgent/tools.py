import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

DATASET_DIR = "dataset"
DEFAULT_DATA_FILE = None
JOB_FILE_GLOB = "*_jobs.json"
LEGACY_JOB_FILES = ("jpmc_ai_jobs_india.json",)
ALLOWED_SORT_FIELDS = {"posted", "title", "primary_location", "id", "company"}


def _resolve_dataset_path(dataset_dir: str = DATASET_DIR) -> Path:
    """Resolve the dataset directory even when the current working directory
    is not the project root. Try the CWD first, then walk up from this
    module's location looking for a folder named `dataset`.
    Returns a Path (may not exist) so callers can raise a clear error.
    """
    # 1) direct path (cwd)
    p = Path(dataset_dir)
    if p.exists():
        return p

    # 2) search upward from this file's directory for the dataset folder
    cur = Path(__file__).resolve().parent
    for _ in range(8):
        candidate = cur / dataset_dir
        if candidate.exists():
            return candidate
        cur = cur.parent

    # 3) fallback to provided path (may not exist) so callers can raise
    return Path(dataset_dir)


def _safe_date_from_iso(value: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _infer_company_from_path(path: Path) -> str:
    stem = path.stem.lower()
    if "jpmc" in stem:
        return "JPMC"
    if "jpmorgan" in stem:
        return "JPMC"
    if "oracle" in stem:
        return "Oracle"
    if stem.endswith("_jobs"):
        stem = stem[:-5]
    return stem


def _normalized_job(job: dict[str, Any], source_file: Path | None = None) -> dict[str, Any]:
    inferred_company = _infer_company_from_path(source_file) if source_file else ""
    company = str(job.get("company") or inferred_company)
    return {
        "id": str(job.get("id", "")),
        "title": job.get("title", ""),
        "primary_location": job.get("primary_location", ""),
        "work_location": job.get("work_location", ""),
        "other_locations": job.get("other_locations", []) or [],
        "workplace_type": job.get("workplace_type", ""),
        "category": job.get("category", ""),
        "organization": job.get("organization", ""),
        "posted": job.get("posted", ""),
        "apply_url": job.get("apply_url", ""),
        "scraped_at": job.get("scraped_at", ""),
        "company": company,
        "source_file": str(source_file) if source_file else "",
    }


def _load_jobs_from_file(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Invalid jobs JSON format in {path}: expected a list.")

    jobs = []
    for item in data:
        if not isinstance(item, dict):
            continue
        # Ignore non-job records (e.g., batch config files with no id/title).
        if "id" not in item and "title" not in item:
            continue
        jobs.append(_normalized_job(item, source_file=path))
    return jobs


def _discover_job_files(dataset_path: Path) -> list[Path]:
    # If the provided path doesn't exist, try to resolve it relative to
    # the project layout so callers can invoke the module from any CWD.
    if not dataset_path.exists():
        dataset_path = _resolve_dataset_path(str(dataset_path))

    if not dataset_path.exists():
        return []

    files = sorted(dataset_path.glob(JOB_FILE_GLOB))
    # Prefer legacy files first when present.
    for legacy_name in LEGACY_JOB_FILES:
        legacy_path = dataset_path / legacy_name
        if legacy_path.exists() and legacy_path not in files:
            files.insert(0, legacy_path)
    return files


def _load_jobs(data_file: str | None = DEFAULT_DATA_FILE, company: str | None = None) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []

    if data_file:
        path = Path(data_file)
        if not path.exists():
            raise FileNotFoundError(f"Data file not found: {data_file}")
        jobs.extend(_load_jobs_from_file(path))
    else:
        dataset_path = _resolve_dataset_path(DATASET_DIR)
        if not dataset_path.exists():
            raise FileNotFoundError(
                f"Dataset folder not found: {dataset_path} (looked for '{DATASET_DIR}')"
            )

        json_files = _discover_job_files(dataset_path)
        if not json_files:
            raise FileNotFoundError(
                f"No job JSON files found in: {dataset_path} (expected pattern: {JOB_FILE_GLOB})"
            )

        for path in json_files:
            jobs.extend(_load_jobs_from_file(path))

    if company:
        company_q = company.strip().lower()
        jobs = [job for job in jobs if company_q in str(job.get("company", "")).lower()]

    return jobs


def _sort_jobs(
    jobs: list[dict[str, Any]],
    sort_by: str = "posted",
    sort_order: str = "desc",
) -> list[dict[str, Any]]:
    if sort_by not in ALLOWED_SORT_FIELDS:
        sort_by = "posted"

    reverse = sort_order.lower() == "desc"

    def sort_key(job: dict[str, Any]) -> tuple[Any, str]:
        value = job.get(sort_by, "")
        if sort_by == "posted":
            posted = _safe_date_from_iso(str(value))
            return ((posted or date.min), job.get("id", ""))
        return (str(value).lower(), job.get("id", ""))

    return sorted(jobs, key=sort_key, reverse=reverse)


def _paginate(jobs: list[dict[str, Any]], limit: int = 25, offset: int = 0) -> list[dict[str, Any]]:
    safe_limit = max(1, min(limit, 200))
    safe_offset = max(0, offset)
    return jobs[safe_offset : safe_offset + safe_limit]


def _success_response(
    jobs: list[dict[str, Any]],
    *,
    filters: dict[str, Any],
    limit: int,
    offset: int,
    sort_by: str,
    sort_order: str,
) -> dict[str, Any]:
    sorted_jobs = _sort_jobs(jobs, sort_by=sort_by, sort_order=sort_order)
    paged_jobs = _paginate(sorted_jobs, limit=limit, offset=offset)
    return {
        "status": "success",
        "filters": filters,
        "sort": {"by": sort_by, "order": sort_order.lower()},
        "pagination": {
            "limit": max(1, min(limit, 200)),
            "offset": max(0, offset),
            "returned": len(paged_jobs),
            "total": len(sorted_jobs),
        },
        "jobs": paged_jobs,
    }


def _error_response(message: str) -> dict[str, Any]:
    return {"status": "error", "message": message}


def get_all_jobs(
    data_file: str | None = DEFAULT_DATA_FILE,
    company: str | None = None,
    limit: int = 25,
    offset: int = 0,
    sort_by: str = "posted",
    sort_order: str = "desc",
) -> dict[str, Any]:
    try:
        jobs = _load_jobs(data_file, company=company)
        return _success_response(
            jobs,
            filters={"company": company, "data_file": data_file},
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception as e:
        return _error_response(str(e))


def get_jobs_by_location(
    location: str,
    data_file: str | None = DEFAULT_DATA_FILE,
    company: str | None = None,
    limit: int = 25,
    offset: int = 0,
    sort_by: str = "posted",
    sort_order: str = "desc",
) -> dict[str, Any]:
    try:
        location_query = (location or "").strip().lower()
        jobs = _load_jobs(data_file, company=company)

        filtered = []
        for job in jobs:
            searchable_locations = [
                str(job.get("primary_location", "")),
                str(job.get("work_location", "")),
                *[str(x) for x in job.get("other_locations", [])],
            ]
            haystack = " | ".join(searchable_locations).lower()
            if location_query and location_query in haystack:
                filtered.append(job)

        return _success_response(
            filtered,
            filters={"location": location, "company": company, "data_file": data_file},
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception as e:
        return _error_response(str(e))


def get_recent_jobs(
    days: int = 7,
    reference_date: str | None = None,
    data_file: str | None = DEFAULT_DATA_FILE,
    company: str | None = None,
    limit: int = 25,
    offset: int = 0,
    sort_by: str = "posted",
    sort_order: str = "desc",
) -> dict[str, Any]:
    try:
        jobs = _load_jobs(data_file, company=company)
        safe_days = max(1, days)

        ref = date.fromisoformat(reference_date) if reference_date else datetime.now().date()
        cutoff = ref - timedelta(days=safe_days)

        filtered = []
        for job in jobs:
            posted = _safe_date_from_iso(str(job.get("posted", "")))
            if posted is not None and posted >= cutoff:
                filtered.append(job)

        return _success_response(
            filtered,
            filters={
                "days": safe_days,
                "reference_date": ref.isoformat(),
                "company": company,
                "data_file": data_file,
            },
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception as e:
        return _error_response(str(e))


def get_jobs_by_posted_date_range(
    start_date: str,
    end_date: str,
    data_file: str | None = DEFAULT_DATA_FILE,
    company: str | None = None,
    limit: int = 25,
    offset: int = 0,
    sort_by: str = "posted",
    sort_order: str = "desc",
) -> dict[str, Any]:
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)

        if end < start:
            return _error_response("end_date must be greater than or equal to start_date")

        jobs = _load_jobs(data_file, company=company)
        filtered = []
        for job in jobs:
            posted = _safe_date_from_iso(str(job.get("posted", "")))
            if posted is not None and start <= posted <= end:
                filtered.append(job)

        return _success_response(
            filtered,
            filters={
                "start_date": start_date,
                "end_date": end_date,
                "company": company,
                "data_file": data_file,
            },
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception as e:
        return _error_response(str(e))


def get_jobs_by_keyword(
    keyword: str,
    data_file: str | None = DEFAULT_DATA_FILE,
    company: str | None = None,
    limit: int = 25,
    offset: int = 0,
    sort_by: str = "posted",
    sort_order: str = "desc",
) -> dict[str, Any]:
    try:
        query = (keyword or "").strip().lower()
        jobs = _load_jobs(data_file, company=company)

        filtered = []
        for job in jobs:
            haystack = " | ".join(
                [
                    str(job.get("title", "")),
                    str(job.get("category", "")),
                    str(job.get("organization", "")),
                    str(job.get("workplace_type", "")),
                    str(job.get("company", "")),
                ]
            ).lower()
            if query and query in haystack:
                filtered.append(job)

        return _success_response(
            filtered,
            filters={"keyword": keyword, "company": company, "data_file": data_file},
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception as e:
        return _error_response(str(e))


def search_jobs(
    location: str | None = None,
    keyword: str | None = None,
    company: str | None = None,
    days: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    workplace_type: str | None = None,
    category: str | None = None,
    data_file: str | None = DEFAULT_DATA_FILE,
    limit: int = 25,
    offset: int = 0,
    sort_by: str = "posted",
    sort_order: str = "desc",
) -> dict[str, Any]:
    """Combined filter tool for agent usage. All filters are AND-ed when provided."""
    try:
        jobs = _load_jobs(data_file, company=company)

        location_q = (location or "").strip().lower()
        keyword_q = (keyword or "").strip().lower()
        workplace_q = (workplace_type or "").strip().lower()
        category_q = (category or "").strip().lower()

        start = date.fromisoformat(start_date) if start_date else None
        end = date.fromisoformat(end_date) if end_date else None
        if start and end and end < start:
            return _error_response("end_date must be greater than or equal to start_date")

        ref = datetime.now().date()
        cutoff = ref - timedelta(days=max(1, days)) if days is not None else None

        filtered = []
        for job in jobs:
            posted = _safe_date_from_iso(str(job.get("posted", "")))

            if location_q:
                searchable_locations = [
                    str(job.get("primary_location", "")),
                    str(job.get("work_location", "")),
                    *[str(x) for x in job.get("other_locations", [])],
                ]
                if location_q not in " | ".join(searchable_locations).lower():
                    continue

            if keyword_q:
                keyword_haystack = " | ".join(
                    [
                        str(job.get("title", "")),
                        str(job.get("category", "")),
                        str(job.get("organization", "")),
                        str(job.get("workplace_type", "")),
                        str(job.get("company", "")),
                    ]
                ).lower()
                if keyword_q not in keyword_haystack:
                    continue

            if workplace_q and workplace_q not in str(job.get("workplace_type", "")).lower():
                continue

            if category_q and category_q not in str(job.get("category", "")).lower():
                continue

            if cutoff is not None and (posted is None or posted < cutoff):
                continue

            if start is not None and (posted is None or posted < start):
                continue

            if end is not None and (posted is None or posted > end):
                continue

            filtered.append(job)

        return _success_response(
            filtered,
            filters={
                "location": location,
                "keyword": keyword,
                "company": company,
                "days": days,
                "start_date": start_date,
                "end_date": end_date,
                "workplace_type": workplace_type,
                "category": category,
                "data_file": data_file,
            },
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception as e:
        return _error_response(str(e))


def get_job_filter_metadata(data_file: str | None = DEFAULT_DATA_FILE) -> dict[str, Any]:
    """Returns available filter values discovered in dataset(s)."""
    try:
        jobs = _load_jobs(data_file)

        locations = sorted(
            {
                str(job.get("primary_location", "")).strip()
                for job in jobs
                if str(job.get("primary_location", "")).strip()
            }
        )
        workplace_types = sorted(
            {
                str(job.get("workplace_type", "")).strip()
                for job in jobs
                if str(job.get("workplace_type", "")).strip()
            }
        )
        categories = sorted(
            {
                str(job.get("category", "")).strip()
                for job in jobs
                if str(job.get("category", "")).strip()
            }
        )
        companies = sorted(
            {
                str(job.get("company", "")).strip()
                for job in jobs
                if str(job.get("company", "")).strip()
            }
        )

        posted_dates = [_safe_date_from_iso(str(job.get("posted", ""))) for job in jobs]
        posted_dates = [d for d in posted_dates if d is not None]

        return {
            "status": "success",
            "counts": {
                "jobs": len(jobs),
                "locations": len(locations),
                "workplace_types": len(workplace_types),
                "categories": len(categories),
                "companies": len(companies),
            },
            "date_range": {
                "min_posted": min(posted_dates).isoformat() if posted_dates else None,
                "max_posted": max(posted_dates).isoformat() if posted_dates else None,
            },
            "companies": companies,
            "locations": locations,
            "workplace_types": workplace_types,
            "categories": categories,
        }
    except Exception as e:
        return _error_response(str(e))


def extract_job_details_from_url(url: str, timeout_seconds: int = 20) -> dict[str, Any]:
    """
    Extract job details from a job page URL using HTML parsing.
    Designed for pages containing:
    - h1.job-details__title
    - div.job-details__subtitle
    - .job-meta__item blocks
    - div.job-details__section blocks
    """
    try:
        try:
            import requests
            from bs4 import BeautifulSoup
        except Exception as import_err:
            return _error_response(
                f"Missing dependency for scraping: {import_err}. "
                "Install with: pip install requests beautifulsoup4"
            )

        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=timeout_seconds)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        job: dict[str, Any] = {"url": url}

        title = soup.find("h1", class_="job-details__title")
        job["title"] = title.get_text(strip=True) if title else None

        location = soup.find("div", class_="job-details__subtitle")
        job["location"] = location.get_text(strip=True) if location else None

        meta_items = soup.select(".job-meta__item")
        for item in meta_items:
            name = item.find("span", class_="job-meta__title")
            value = item.find("span", class_="job-meta__subitem")
            if name and value:
                job[name.get_text(strip=True)] = value.get_text(strip=True)

        sections = soup.find_all("div", class_="job-details__section")
        for section in sections:
            header = section.find("h2")
            content = section.find("div", class_="job-details__description-content")
            if header and content:
                job[header.get_text(strip=True)] = content.get_text(
                    separator="\n", strip=True
                )

        return {
            "status": "success",
            "job": job,
        }
    except Exception as e:
        return _error_response(str(e))
