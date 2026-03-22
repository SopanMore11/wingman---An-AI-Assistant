from __future__ import annotations

import csv
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

DB_ENV_VAR = "WINGMAN_DB_PATH"
DEFAULT_DB_NAME = "dataset/wingmandb.db"
DEFAULT_EXPENSE_CSV = "dataset/my_expences.csv"
JOB_FILE_GLOB = "*_jobs.json"
LEGACY_JOB_FILES = ("jpmc_ai_jobs_india.json",)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_db_path(db_file: str | None = None) -> Path:
    if db_file:
        return Path(db_file)

    env_value = str(os.getenv(DB_ENV_VAR, "")).strip()
    if env_value:
        return Path(env_value)

    return _repo_root() / DEFAULT_DB_NAME


def resolve_expense_csv_path(csv_file: str | None = None) -> Path:
    if csv_file:
        return Path(csv_file)
    return _repo_root() / DEFAULT_EXPENSE_CSV


def resolve_dataset_dir(dataset_dir: str = "dataset") -> Path:
    direct = Path(dataset_dir)
    if direct.exists():
        return direct

    repo_candidate = _repo_root() / dataset_dir
    if repo_candidate.exists():
        return repo_candidate

    return direct


def get_connection(db_file: str | None = None) -> sqlite3.Connection:
    db_path = resolve_db_path(db_file)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database(db_file: str | None = None) -> Path:
    db_path = resolve_db_path(db_file)
    with get_connection(str(db_path)) as conn:
        _create_schema(conn)
        _bootstrap_expenses(conn)
        _bootstrap_jobs(conn)
    return db_path


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            expense_date TEXT NOT NULL,
            day TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL DEFAULT '',
            primary_location TEXT NOT NULL DEFAULT '',
            work_location TEXT NOT NULL DEFAULT '',
            other_locations_json TEXT NOT NULL DEFAULT '[]',
            workplace_type TEXT NOT NULL DEFAULT '',
            category TEXT NOT NULL DEFAULT '',
            organization TEXT NOT NULL DEFAULT '',
            posted TEXT NOT NULL DEFAULT '',
            apply_url TEXT NOT NULL DEFAULT '',
            scraped_at TEXT NOT NULL DEFAULT '',
            company TEXT NOT NULL DEFAULT '',
            source_file TEXT NOT NULL DEFAULT '',
            source_endpoint TEXT NOT NULL DEFAULT '',
            flex_fields_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(expense_date);
        CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category);
        CREATE INDEX IF NOT EXISTS idx_jobs_posted ON jobs(posted);
        CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company);
        CREATE INDEX IF NOT EXISTS idx_jobs_location ON jobs(primary_location);
        """
    )


def _table_count(conn: sqlite3.Connection, table_name: str) -> int:
    row = conn.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()
    return int(row["count"]) if row else 0


def _bootstrap_expenses(conn: sqlite3.Connection) -> None:
    if _table_count(conn, "expenses") > 0:
        return

    csv_path = resolve_expense_csv_path()
    if not csv_path.exists():
        return

    rows: list[tuple[str, str, str, str, float, str]] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw_row in reader:
            if not raw_row:
                continue

            try:
                amount = float(raw_row.get("Amount", 0) or 0)
            except (TypeError, ValueError):
                amount = 0.0

            rows.append(
                (
                    str(raw_row.get("Date", "") or "").strip(),
                    str(raw_row.get("Day", "") or "").strip(),
                    str(raw_row.get("Category", "") or "").strip(),
                    str(raw_row.get("Description", "") or "").strip(),
                    amount,
                    str(raw_row.get("Notes", "") or "").strip(),
                )
            )

    if rows:
        conn.executemany(
            """
            INSERT INTO expenses (
                expense_date, day, category, description, amount, notes
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def _bootstrap_jobs(conn: sqlite3.Connection) -> None:
    if _table_count(conn, "jobs") > 0:
        return

    dataset_dir = resolve_dataset_dir()
    if not dataset_dir.exists():
        return

    json_files = sorted(dataset_dir.glob(JOB_FILE_GLOB))
    for legacy_name in LEGACY_JOB_FILES:
        legacy_path = dataset_dir / legacy_name
        if legacy_path.exists() and legacy_path not in json_files:
            json_files.insert(0, legacy_path)

    rows: list[tuple[str, str, str, str, str, str, str, str, str, str, str, str, str, str, str]] = []
    for path in json_files:
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            continue

        if not isinstance(data, list):
            continue

        inferred_company = _infer_company_from_path(path)
        for item in data:
            if not isinstance(item, dict):
                continue

            if "id" not in item and "title" not in item:
                continue

            rows.append(
                (
                    str(item.get("id", "") or ""),
                    str(item.get("title", "") or ""),
                    str(item.get("primary_location", "") or ""),
                    str(item.get("work_location", "") or ""),
                    json.dumps(item.get("other_locations", []) or []),
                    str(item.get("workplace_type", "") or ""),
                    str(item.get("category", "") or ""),
                    str(item.get("organization", "") or ""),
                    str(item.get("posted", "") or ""),
                    str(item.get("apply_url", "") or ""),
                    str(item.get("scraped_at", "") or ""),
                    str(item.get("company") or inferred_company or ""),
                    str(path),
                    str(item.get("source_endpoint", "") or ""),
                    json.dumps(item.get("flex_fields", {}) or {}),
                )
            )

    if rows:
        conn.executemany(
            """
            INSERT OR REPLACE INTO jobs (
                id, title, primary_location, work_location, other_locations_json,
                workplace_type, category, organization, posted, apply_url,
                scraped_at, company, source_file, source_endpoint, flex_fields_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def _infer_company_from_path(path: Path) -> str:
    stem = path.stem.lower()
    if "jpmc" in stem or "jpmorgan" in stem:
        return "JPMC"
    if "oracle" in stem:
        return "Oracle"
    if stem.endswith("_jobs"):
        stem = stem[:-5]
    return stem
