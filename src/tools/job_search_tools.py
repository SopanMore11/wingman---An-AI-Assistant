from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from src.tools.crawlerEngine import (
    COMPANY_KEY_ALIASES,
    canonical_company_key,
    parse_keywords,
    run_crawler,
)
from src.data.sqlite_store import get_connection, initialize_database, upsert_jobs_from_json_files

ALLOWED_SORT_FIELDS = {
    "posted": "posted",
    "title": "title",
    "primary_location": "primary_location",
    "id": "id",
    "company": "company",
}
COMPANY_BATCH_FILE = "dataset/companies_batch.json"


def _db_path() -> str:
    return str(initialize_database())


def _normalize_job(row: Any) -> dict[str, Any]:
    return {
        "id": str(row["id"] or ""),
        "title": row["title"] or "",
        "primary_location": row["primary_location"] or "",
        "work_location": row["work_location"] or "",
        "other_locations": json.loads(row["other_locations_json"] or "[]"),
        "workplace_type": row["workplace_type"] or "",
        "category": row["category"] or "",
        "organization": row["organization"] or "",
        "posted": row["posted"] or "",
        "apply_url": row["apply_url"] or "",
        "scraped_at": row["scraped_at"] or "",
        "company": row["company"] or "",
        "source_file": row["source_file"] or "",
        "source_endpoint": row["source_endpoint"] or "",
        "flex_fields": json.loads(row["flex_fields_json"] or "{}"),
    }


def _resolve_source_file(data_file: str | None) -> str | None:
    if not data_file:
        return None
    return str(Path(data_file))


def _build_common_filters(
    *,
    company: str | None = None,
    data_file: str | None = None,
) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []

    if company:
        clauses.append("LOWER(company) LIKE ?")
        params.append(f"%{company.strip().lower()}%")

    source_file = _resolve_source_file(data_file)
    if source_file:
        clauses.append("source_file = ?")
        params.append(source_file)

    where_sql = " WHERE " + " AND ".join(clauses) if clauses else ""
    return where_sql, params


def _safe_sort(sort_by: str = "posted", sort_order: str = "desc") -> tuple[str, str]:
    column = ALLOWED_SORT_FIELDS.get(sort_by, "posted")
    direction = "DESC" if sort_order.lower() == "desc" else "ASC"
    if column == "posted":
        return f"{column} {direction}, id {direction}", direction
    return f"{column} {direction}, id ASC", direction


def _run_job_query(
    *,
    filters: dict[str, Any],
    where_sql: str,
    params: list[Any],
    limit: int,
    offset: int,
    sort_by: str,
    sort_order: str,
) -> dict[str, Any]:
    db_path = _db_path()
    safe_limit = max(1, min(limit, 200))
    safe_offset = max(0, offset)
    order_sql, _ = _safe_sort(sort_by, sort_order)

    with get_connection(db_path) as conn:
        total = conn.execute(
            f"SELECT COUNT(*) AS count FROM jobs{where_sql}",
            params,
        ).fetchone()["count"]
        rows = conn.execute(
            f"""
            SELECT *
            FROM jobs
            {where_sql}
            ORDER BY {order_sql}
            LIMIT ? OFFSET ?
            """,
            params + [safe_limit, safe_offset],
        ).fetchall()

    return {
        "status": "success",
        "filters": filters,
        "sort": {"by": sort_by if sort_by in ALLOWED_SORT_FIELDS else "posted", "order": sort_order.lower()},
        "pagination": {
            "limit": safe_limit,
            "offset": safe_offset,
            "returned": len(rows),
            "total": int(total),
        },
        "jobs": [_normalize_job(row) for row in rows],
        "db_path": db_path,
    }


def _error_response(message: str) -> dict[str, Any]:
    return {"status": "error", "message": message}


def _resolve_company_config(company: str) -> dict[str, Any]:
    batch_path = Path(COMPANY_BATCH_FILE)
    if not batch_path.exists():
        raise FileNotFoundError(f"Company batch file not found: {COMPANY_BATCH_FILE}")

    with batch_path.open("r", encoding="utf-8") as file:
        configs = json.load(file)

    if not isinstance(configs, list):
        raise ValueError("Company batch file must contain a list of company configs.")

    company_query = (company or "").strip().lower()
    if not company_query:
        raise ValueError("company is required")

    canonical_query = COMPANY_KEY_ALIASES.get(company_query, canonical_company_key(company_query))

    for config in configs:
        if not isinstance(config, dict):
            continue
        config_company = str(config.get("company", "") or "")
        config_key = canonical_company_key(config_company)
        if company_query in config_company.lower() or canonical_query == config_key:
            return config

    raise ValueError(f"Unsupported company '{company}'. Add it to {COMPANY_BATCH_FILE} first.")


def refresh_company_jobs(
    company: str,
    keywords: str | None = None,
    output_dir: str = "dataset",
) -> dict[str, Any]:
    """Crawl the latest listings for a supported company and sync them into SQLite."""
    try:
        config = _resolve_company_config(company)
        crawl_result = run_crawler(
            company_name=str(config["company"]),
            endpoint=str(config["endpoint"]),
            keywords=parse_keywords(keywords if keywords is not None else config.get("keywords")),
            site_number=config.get("site_number"),
            location_id=config.get("location_id"),
            category_id=config.get("category_id"),
            output_dir=output_dir,
        )

        if crawl_result.get("status") != "success":
            return crawl_result

        sync_result = upsert_jobs_from_json_files([str(crawl_result["output_json"])])
        db_path = _db_path()
        with get_connection(db_path) as conn:
            total_jobs = conn.execute(
                "SELECT COUNT(*) AS count FROM jobs WHERE LOWER(company) LIKE ?",
                (f"%{str(config['company']).lower()}%",),
            ).fetchone()["count"]

        return {
            "status": "success",
            "company": config["company"],
            "message": f"Refreshed latest listings for {config['company']} and synced them to SQLite.",
            "crawler": crawl_result,
            "sync": sync_result,
            "company_job_count": int(total_jobs),
            "db_path": db_path,
        }
    except Exception as exc:
        return _error_response(str(exc))


def get_all_jobs(
    data_file: str | None = None,
    company: str | None = None,
    limit: int = 25,
    offset: int = 0,
    sort_by: str = "posted",
    sort_order: str = "desc",
) -> dict[str, Any]:
    try:
        where_sql, params = _build_common_filters(company=company, data_file=data_file)
        return _run_job_query(
            filters={"company": company, "data_file": data_file},
            where_sql=where_sql,
            params=params,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception as exc:
        return _error_response(str(exc))


def get_jobs_by_location(
    location: str,
    data_file: str | None = None,
    company: str | None = None,
    limit: int = 25,
    offset: int = 0,
    sort_by: str = "posted",
    sort_order: str = "desc",
) -> dict[str, Any]:
    try:
        location_query = (location or "").strip().lower()
        where_sql, params = _build_common_filters(company=company, data_file=data_file)
        location_clause = """
            (
                LOWER(primary_location) LIKE ?
                OR LOWER(work_location) LIKE ?
                OR LOWER(other_locations_json) LIKE ?
            )
        """
        where_sql += (" AND " if where_sql else " WHERE ") + location_clause
        pattern = f"%{location_query}%"
        params.extend([pattern, pattern, pattern])

        return _run_job_query(
            filters={"location": location, "company": company, "data_file": data_file},
            where_sql=where_sql,
            params=params,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception as exc:
        return _error_response(str(exc))


def get_recent_jobs(
    days: int = 7,
    reference_date: str | None = None,
    data_file: str | None = None,
    company: str | None = None,
    limit: int = 25,
    offset: int = 0,
    sort_by: str = "posted",
    sort_order: str = "desc",
) -> dict[str, Any]:
    try:
        safe_days = max(1, days)
        ref = date.fromisoformat(reference_date) if reference_date else datetime.now().date()
        cutoff = (ref - timedelta(days=safe_days)).isoformat()

        where_sql, params = _build_common_filters(company=company, data_file=data_file)
        where_sql += (" AND " if where_sql else " WHERE ") + "posted >= ?"
        params.append(cutoff)

        return _run_job_query(
            filters={
                "days": safe_days,
                "reference_date": ref.isoformat(),
                "company": company,
                "data_file": data_file,
            },
            where_sql=where_sql,
            params=params,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception as exc:
        return _error_response(str(exc))


def get_jobs_by_posted_date_range(
    start_date: str,
    end_date: str,
    data_file: str | None = None,
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

        where_sql, params = _build_common_filters(company=company, data_file=data_file)
        where_sql += (" AND " if where_sql else " WHERE ") + "posted BETWEEN ? AND ?"
        params.extend([start.isoformat(), end.isoformat()])

        return _run_job_query(
            filters={
                "start_date": start_date,
                "end_date": end_date,
                "company": company,
                "data_file": data_file,
            },
            where_sql=where_sql,
            params=params,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception as exc:
        return _error_response(str(exc))


def get_jobs_by_keyword(
    keyword: str,
    data_file: str | None = None,
    company: str | None = None,
    limit: int = 25,
    offset: int = 0,
    sort_by: str = "posted",
    sort_order: str = "desc",
) -> dict[str, Any]:
    try:
        query = (keyword or "").strip().lower()
        where_sql, params = _build_common_filters(company=company, data_file=data_file)
        where_sql += (" AND " if where_sql else " WHERE ") + """
            (
                LOWER(title) LIKE ?
                OR LOWER(category) LIKE ?
                OR LOWER(organization) LIKE ?
                OR LOWER(workplace_type) LIKE ?
                OR LOWER(company) LIKE ?
            )
        """
        pattern = f"%{query}%"
        params.extend([pattern, pattern, pattern, pattern, pattern])

        return _run_job_query(
            filters={"keyword": keyword, "company": company, "data_file": data_file},
            where_sql=where_sql,
            params=params,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception as exc:
        return _error_response(str(exc))


def search_jobs(
    location: str | None = None,
    keyword: str | None = None,
    company: str | None = None,
    days: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    workplace_type: str | None = None,
    category: str | None = None,
    data_file: str | None = None,
    limit: int = 25,
    offset: int = 0,
    sort_by: str = "posted",
    sort_order: str = "desc",
) -> dict[str, Any]:
    try:
        where_sql, params = _build_common_filters(company=company, data_file=data_file)

        if start_date:
            start = date.fromisoformat(start_date)
        else:
            start = None

        if end_date:
            end = date.fromisoformat(end_date)
        else:
            end = None

        if start and end and end < start:
            return _error_response("end_date must be greater than or equal to start_date")

        if location:
            pattern = f"%{location.strip().lower()}%"
            where_sql += (" AND " if where_sql else " WHERE ") + """
                (
                    LOWER(primary_location) LIKE ?
                    OR LOWER(work_location) LIKE ?
                    OR LOWER(other_locations_json) LIKE ?
                )
            """
            params.extend([pattern, pattern, pattern])

        if keyword:
            pattern = f"%{keyword.strip().lower()}%"
            where_sql += (" AND " if where_sql else " WHERE ") + """
                (
                    LOWER(title) LIKE ?
                    OR LOWER(category) LIKE ?
                    OR LOWER(organization) LIKE ?
                    OR LOWER(workplace_type) LIKE ?
                    OR LOWER(company) LIKE ?
                )
            """
            params.extend([pattern, pattern, pattern, pattern, pattern])

        if workplace_type:
            where_sql += (" AND " if where_sql else " WHERE ") + "LOWER(workplace_type) LIKE ?"
            params.append(f"%{workplace_type.strip().lower()}%")

        if category:
            where_sql += (" AND " if where_sql else " WHERE ") + "LOWER(category) LIKE ?"
            params.append(f"%{category.strip().lower()}%")

        if days is not None:
            cutoff = (datetime.now().date() - timedelta(days=max(1, days))).isoformat()
            where_sql += (" AND " if where_sql else " WHERE ") + "posted >= ?"
            params.append(cutoff)

        if start is not None:
            where_sql += (" AND " if where_sql else " WHERE ") + "posted >= ?"
            params.append(start.isoformat())

        if end is not None:
            where_sql += (" AND " if where_sql else " WHERE ") + "posted <= ?"
            params.append(end.isoformat())

        return _run_job_query(
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
            where_sql=where_sql,
            params=params,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception as exc:
        return _error_response(str(exc))


def get_job_filter_metadata(data_file: str | None = None) -> dict[str, Any]:
    try:
        db_path = _db_path()
        where_sql, params = _build_common_filters(data_file=data_file)

        with get_connection(db_path) as conn:
            total_jobs = conn.execute(
                f"SELECT COUNT(*) AS count FROM jobs{where_sql}",
                params,
            ).fetchone()["count"]
            min_max = conn.execute(
                f"SELECT MIN(posted) AS min_posted, MAX(posted) AS max_posted FROM jobs{where_sql}",
                params,
            ).fetchone()

            def distinct_values(column: str) -> list[str]:
                rows = conn.execute(
                    f"""
                    SELECT DISTINCT {column} AS value
                    FROM jobs
                    {where_sql}
                    AND {column} != ''
                    """ if where_sql else f"""
                    SELECT DISTINCT {column} AS value
                    FROM jobs
                    WHERE {column} != ''
                    """,
                    params,
                ).fetchall()
                return sorted(str(row["value"]).strip() for row in rows if str(row["value"]).strip())

            locations = distinct_values("primary_location")
            workplace_types = distinct_values("workplace_type")
            categories = distinct_values("category")
            companies = distinct_values("company")

        return {
            "status": "success",
            "counts": {
                "jobs": int(total_jobs),
                "locations": len(locations),
                "workplace_types": len(workplace_types),
                "categories": len(categories),
                "companies": len(companies),
            },
            "date_range": {
                "min_posted": min_max["min_posted"],
                "max_posted": min_max["max_posted"],
            },
            "companies": companies,
            "locations": locations,
            "workplace_types": workplace_types,
            "categories": categories,
            "db_path": db_path,
        }
    except Exception as exc:
        return _error_response(str(exc))


def extract_job_details_from_url(url: str, timeout_seconds: int = 20) -> dict[str, Any]:
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
                job[header.get_text(strip=True)] = content.get_text(separator="\n", strip=True)

        return {
            "status": "success",
            "job": job,
        }
    except Exception as exc:
        return _error_response(str(exc))
