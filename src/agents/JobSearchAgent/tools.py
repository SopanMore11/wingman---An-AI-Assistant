import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

DEFAULT_DATA_FILE = "dataset/jpmc_ai_jobs_india.json"
ALLOWED_SORT_FIELDS = {"posted", "title", "primary_location", "id"}


def _safe_date_from_iso(value: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _normalized_job(job: dict[str, Any]) -> dict[str, Any]:
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
    }


def _load_jobs(data_file: str = DEFAULT_DATA_FILE) -> list[dict[str, Any]]:
    path = Path(data_file)
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {data_file}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Invalid jobs JSON format: expected a list.")

    return [_normalized_job(item) for item in data if isinstance(item, dict)]


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
    data_file: str = DEFAULT_DATA_FILE,
    limit: int = 25,
    offset: int = 0,
    sort_by: str = "posted",
    sort_order: str = "desc",
) -> dict[str, Any]:
    try:
        jobs = _load_jobs(data_file)
        return _success_response(
            jobs,
            filters={},
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception as e:
        return _error_response(str(e))


def get_jobs_by_location(
    location: str,
    data_file: str = DEFAULT_DATA_FILE,
    limit: int = 25,
    offset: int = 0,
    sort_by: str = "posted",
    sort_order: str = "desc",
) -> dict[str, Any]:
    try:
        location_query = (location or "").strip().lower()
        jobs = _load_jobs(data_file)

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
            filters={"location": location},
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
    data_file: str = DEFAULT_DATA_FILE,
    limit: int = 25,
    offset: int = 0,
    sort_by: str = "posted",
    sort_order: str = "desc",
) -> dict[str, Any]:
    try:
        jobs = _load_jobs(data_file)
        safe_days = max(1, days)

        if reference_date:
            ref = date.fromisoformat(reference_date)
        else:
            ref = datetime.now().date()

        cutoff = ref - timedelta(days=safe_days)

        filtered = []
        for job in jobs:
            posted = _safe_date_from_iso(str(job.get("posted", "")))
            if posted is not None and posted >= cutoff:
                filtered.append(job)

        return _success_response(
            filtered,
            filters={"days": safe_days, "reference_date": ref.isoformat()},
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
    data_file: str = DEFAULT_DATA_FILE,
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

        jobs = _load_jobs(data_file)
        filtered = []
        for job in jobs:
            posted = _safe_date_from_iso(str(job.get("posted", "")))
            if posted is not None and start <= posted <= end:
                filtered.append(job)

        return _success_response(
            filtered,
            filters={"start_date": start_date, "end_date": end_date},
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception as e:
        return _error_response(str(e))


def get_jobs_by_keyword(
    keyword: str,
    data_file: str = DEFAULT_DATA_FILE,
    limit: int = 25,
    offset: int = 0,
    sort_by: str = "posted",
    sort_order: str = "desc",
) -> dict[str, Any]:
    try:
        query = (keyword or "").strip().lower()
        jobs = _load_jobs(data_file)

        filtered = []
        for job in jobs:
            haystack = " | ".join(
                [
                    str(job.get("title", "")),
                    str(job.get("category", "")),
                    str(job.get("organization", "")),
                    str(job.get("workplace_type", "")),
                ]
            ).lower()
            if query and query in haystack:
                filtered.append(job)

        return _success_response(
            filtered,
            filters={"keyword": keyword},
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
    days: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    workplace_type: str | None = None,
    category: str | None = None,
    data_file: str = DEFAULT_DATA_FILE,
    limit: int = 25,
    offset: int = 0,
    sort_by: str = "posted",
    sort_order: str = "desc",
) -> dict[str, Any]:
    """
    Combined filter tool for agent usage.
    All filters are optional and AND-ed when provided.
    """
    try:
        jobs = _load_jobs(data_file)

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
                    ]
                ).lower()
                if keyword_q not in keyword_haystack:
                    continue

            if workplace_q and workplace_q not in str(job.get("workplace_type", "")).lower():
                continue

            if category_q and category_q not in str(job.get("category", "")).lower():
                continue

            if cutoff is not None:
                if posted is None or posted < cutoff:
                    continue

            if start is not None:
                if posted is None or posted < start:
                    continue

            if end is not None:
                if posted is None or posted > end:
                    continue

            filtered.append(job)

        return _success_response(
            filtered,
            filters={
                "location": location,
                "keyword": keyword,
                "days": days,
                "start_date": start_date,
                "end_date": end_date,
                "workplace_type": workplace_type,
                "category": category,
            },
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception as e:
        return _error_response(str(e))


def get_job_filter_metadata(data_file: str = DEFAULT_DATA_FILE) -> dict[str, Any]:
    """
    Returns available filter values discovered in dataset.
    """
    try:
        jobs = _load_jobs(data_file)

        locations = sorted(
            {str(job.get("primary_location", "")).strip() for job in jobs if str(job.get("primary_location", "")).strip()}
        )
        workplace_types = sorted(
            {str(job.get("workplace_type", "")).strip() for job in jobs if str(job.get("workplace_type", "")).strip()}
        )
        categories = sorted(
            {str(job.get("category", "")).strip() for job in jobs if str(job.get("category", "")).strip()}
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
            },
            "date_range": {
                "min_posted": min(posted_dates).isoformat() if posted_dates else None,
                "max_posted": max(posted_dates).isoformat() if posted_dates else None,
            },
            "locations": locations,
            "workplace_types": workplace_types,
            "categories": categories,
        }
    except Exception as e:
        return _error_response(str(e))
