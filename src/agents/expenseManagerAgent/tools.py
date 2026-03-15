from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

CSV_ENV_VAR = "EXPENSES_CSV"
DEFAULT_CSV_NAME = "dataset/my_expences.csv"
COLUMNS = ["Date", "Day", "Category", "Description", "Amount", "Notes"]


class ExpenseTools:
    def __init__(self, default_csv_name: str = DEFAULT_CSV_NAME):
        self.default_csv_name = default_csv_name

    def _resolve_csv_path(self, csv_file: str | None = None) -> Path:
        if csv_file:
            return Path(csv_file)

        env_value = str(os.getenv(CSV_ENV_VAR, "")).strip()
        if env_value:
            return Path(env_value)

        # Prefer the repository-level `dataset/my_expences.csv` (project root)
        repo_root = Path(__file__).resolve().parents[3]
        return repo_root / self.default_csv_name

    @staticmethod
    def _empty_df() -> pd.DataFrame:
        return pd.DataFrame(columns=COLUMNS)

    @staticmethod
    def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
        normalized = df.copy()
        for column in COLUMNS:
            if column not in normalized.columns:
                normalized[column] = ""
        normalized = normalized[COLUMNS]
        normalized["Amount"] = pd.to_numeric(normalized["Amount"], errors="coerce").fillna(0.0)
        return normalized

    def _load_expenses(self, csv_path: Path) -> pd.DataFrame:
        if not csv_path.exists():
            return self._empty_df()

        try:
            df = pd.read_csv(csv_path)
            return self._normalize_df(df)
        except Exception:
            return self._empty_df()

    @staticmethod
    def _save_expenses(df: pd.DataFrame, csv_path: Path) -> None:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = csv_path.with_suffix(f"{csv_path.suffix}.tmp")
        df.to_csv(temp_path, index=False)
        os.replace(temp_path, csv_path)

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        return datetime.strptime(date_str, "%Y-%m-%d")

    @staticmethod
    def _build_success(data: dict[str, Any]) -> dict[str, Any]:
        return {"status": "success", **data}

    @staticmethod
    def _build_error(message: str) -> dict[str, Any]:
        return {"status": "error", "message": message}

    # -------------------------------------------------------------------------
    # Original tools
    # -------------------------------------------------------------------------

    def add_daily_expense(
        self,
        date: str,
        category: str,
        description: str,
        amount: float,
        notes: str = "",
        csv_file: str | None = None,
    ) -> dict[str, Any]:
        """Add one expense record.

        Args:
            date:        Date of the expense in YYYY-MM-DD format.
            category:    Broad category, e.g. "Food", "Transport", "Rent".
            description: Short description of what was spent on.
            amount:      Positive number representing how much was spent.
            notes:       (Optional) any extra context you want to remember.
            csv_file:    (Optional) path to a custom CSV file.
        """
        try:
            parsed_date = self._parse_date(date)
        except ValueError:
            return self._build_error("Invalid date format. Expected YYYY-MM-DD.")

        safe_category = (category or "").strip()
        safe_description = (description or "").strip()
        safe_notes = (notes or "").strip()

        if not safe_category:
            return self._build_error("Category is required.")
        if not safe_description:
            return self._build_error("Description is required.")

        try:
            safe_amount = float(amount)
        except (TypeError, ValueError):
            return self._build_error("Amount must be a number.")

        if safe_amount <= 0:
            return self._build_error("Amount must be greater than 0.")

        csv_path = self._resolve_csv_path(csv_file)
        df = self._load_expenses(csv_path)

        new_row = {
            "Date": parsed_date.strftime("%Y-%m-%d"),
            "Day": parsed_date.strftime("%A"),
            "Category": safe_category,
            "Description": safe_description,
            "Amount": safe_amount,
            "Notes": safe_notes,
        }

        if df.empty:
            updated_df = pd.DataFrame([new_row], columns=COLUMNS)
        else:
            updated_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        self._save_expenses(updated_df, csv_path)

        return self._build_success(
            {
                "message": "Expense added.",
                "expense": new_row,
                "total_records": len(updated_df),
                "csv_path": str(csv_path),
            }
        )

    @staticmethod
    def _aggregate_by_category(
        df: pd.DataFrame,
        *,
        year: int,
        month: int | None = None,
        week: int | None = None,
    ) -> dict[str, float]:
        working = df.copy()
        working["Date"] = pd.to_datetime(working["Date"], errors="coerce")
        working = working.dropna(subset=["Date"])

        if month is not None:
            filtered = working[
                (working["Date"].dt.year == year)
                & (working["Date"].dt.month == month)
            ]
        else:
            iso = working["Date"].dt.isocalendar()
            filtered = working[(iso["year"] == year) & (iso["week"] == week)]

        grouped = filtered.groupby("Category", dropna=False)["Amount"].sum().sort_values(ascending=False)
        return {str(k): float(v) for k, v in grouped.to_dict().items()}

    def monthly_category_expense(
        self,
        year: int,
        month: int,
        csv_file: str | None = None,
    ) -> dict[str, Any]:
        """Get category totals for a given month.

        Args:
            year:     4-digit year, e.g. 2025.
            month:    Month number 1–12.
            csv_file: (Optional) path to a custom CSV file.
        """
        if month < 1 or month > 12:
            return self._build_error("Month must be between 1 and 12.")

        csv_path = self._resolve_csv_path(csv_file)
        df = self._load_expenses(csv_path)
        totals = self._aggregate_by_category(df, year=year, month=month)
        return self._build_success(
            {
                "year": year,
                "month": month,
                "category_totals": totals,
                "csv_path": str(csv_path),
            }
        )

    def weekly_category_expense(
        self,
        year: int,
        week: int,
        csv_file: str | None = None,
    ) -> dict[str, Any]:
        """Get category totals for a given ISO week.

        Args:
            year:     4-digit year, e.g. 2025.
            week:     ISO week number 1–53.
            csv_file: (Optional) path to a custom CSV file.
        """
        if week < 1 or week > 53:
            return self._build_error("Week must be between 1 and 53.")

        csv_path = self._resolve_csv_path(csv_file)
        df = self._load_expenses(csv_path)
        totals = self._aggregate_by_category(df, year=year, week=week)
        return self._build_success(
            {
                "year": year,
                "week": week,
                "category_totals": totals,
                "csv_path": str(csv_path),
            }
        )

    # -------------------------------------------------------------------------
    # New tools
    # -------------------------------------------------------------------------

    def get_expense_summary(
        self,
        start_date: str,
        end_date: str,
        csv_file: str | None = None,
    ) -> dict[str, Any]:
        """Get total spending and a per-category breakdown for any date range.

        Useful for ad-hoc periods like a holiday, a trip, or a quarter.

        Args:
            start_date: Start of the range in YYYY-MM-DD format (inclusive).
            end_date:   End of the range in YYYY-MM-DD format (inclusive).
            csv_file:   (Optional) path to a custom CSV file.

        Returns:
            total_amount, record_count, category_totals, and the date range used.
        """
        try:
            start = self._parse_date(start_date)
            end = self._parse_date(end_date)
        except ValueError:
            return self._build_error("Invalid date format. Expected YYYY-MM-DD.")

        if end < start:
            return self._build_error("end_date must be on or after start_date.")

        csv_path = self._resolve_csv_path(csv_file)
        df = self._load_expenses(csv_path)

        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        mask = (df["Date"] >= pd.Timestamp(start)) & (df["Date"] <= pd.Timestamp(end))
        filtered = df[mask]

        category_totals = (
            filtered.groupby("Category", dropna=False)["Amount"]
            .sum()
            .sort_values(ascending=False)
        )

        return self._build_success(
            {
                "start_date": start_date,
                "end_date": end_date,
                "total_amount": float(filtered["Amount"].sum()),
                "record_count": len(filtered),
                "category_totals": {str(k): float(v) for k, v in category_totals.to_dict().items()},
                "csv_path": str(csv_path),
            }
        )

    def search_expenses(
        self,
        keyword: str | None = None,
        category: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        min_amount: float | None = None,
        max_amount: float | None = None,
        csv_file: str | None = None,
    ) -> dict[str, Any]:
        """Search and filter expenses using one or more criteria.

        All filters are optional and combined with AND logic when provided.

        Args:
            keyword:    Text to look for in Description or Notes (case-insensitive).
            category:   Exact category name to filter by (case-insensitive).
            start_date: Only include expenses on or after this date (YYYY-MM-DD).
            end_date:   Only include expenses on or before this date (YYYY-MM-DD).
            min_amount: Only include expenses with amount >= this value.
            max_amount: Only include expenses with amount <= this value.
            csv_file:   (Optional) path to a custom CSV file.

        Returns:
            List of matching expense records and a count.
        """
        csv_path = self._resolve_csv_path(csv_file)
        df = self._load_expenses(csv_path)

        if df.empty:
            return self._build_success({"matches": [], "count": 0, "csv_path": str(csv_path)})

        working = df.copy()
        working["Date"] = pd.to_datetime(working["Date"], errors="coerce")

        if keyword:
            kw = keyword.lower()
            mask = (
                working["Description"].str.lower().str.contains(kw, na=False)
                | working["Notes"].str.lower().str.contains(kw, na=False)
            )
            working = working[mask]

        if category:
            working = working[working["Category"].str.lower() == category.lower()]

        if start_date:
            try:
                start = pd.Timestamp(self._parse_date(start_date))
                working = working[working["Date"] >= start]
            except ValueError:
                return self._build_error("Invalid start_date format. Expected YYYY-MM-DD.")

        if end_date:
            try:
                end = pd.Timestamp(self._parse_date(end_date))
                working = working[working["Date"] <= end]
            except ValueError:
                return self._build_error("Invalid end_date format. Expected YYYY-MM-DD.")

        if min_amount is not None:
            working = working[working["Amount"] >= min_amount]

        if max_amount is not None:
            working = working[working["Amount"] <= max_amount]

        # Convert dates back to strings for a clean JSON-friendly output
        working = working.copy()
        working["Date"] = working["Date"].dt.strftime("%Y-%m-%d").fillna("")

        return self._build_success(
            {
                "matches": working.to_dict(orient="records"),
                "count": len(working),
                "csv_path": str(csv_path),
            }
        )

    def delete_expense(
        self,
        row_index: int,
        csv_file: str | None = None,
    ) -> dict[str, Any]:
        """Delete a single expense by its row index (0-based).

        Use ``search_expenses`` first to find the exact row you want to remove,
        then pass the ``row_index`` from those results here.

        Args:
            row_index: The 0-based position of the row in the CSV (as returned
                       by search_expenses results order).
            csv_file:  (Optional) path to a custom CSV file.

        Returns:
            The deleted expense record and the updated total row count.
        """
        csv_path = self._resolve_csv_path(csv_file)
        df = self._load_expenses(csv_path)

        if df.empty:
            return self._build_error("No expenses found in the file.")

        if row_index < 0 or row_index >= len(df):
            return self._build_error(
                f"row_index {row_index} is out of range. "
                f"Valid range: 0 to {len(df) - 1}."
            )

        deleted_row = df.iloc[row_index].to_dict()
        updated_df = df.drop(index=row_index).reset_index(drop=True)
        self._save_expenses(updated_df, csv_path)

        return self._build_success(
            {
                "message": "Expense deleted.",
                "deleted_expense": deleted_row,
                "remaining_records": len(updated_df),
                "csv_path": str(csv_path),
            }
        )

    def edit_expense(
        self,
        row_index: int,
        category: str | None = None,
        description: str | None = None,
        amount: float | None = None,
        notes: str | None = None,
        csv_file: str | None = None,
    ) -> dict[str, Any]:
        """Update one or more fields of an existing expense record.

        Only the fields you pass will be changed; everything else stays the same.
        Use ``search_expenses`` first to locate the right row index.

        Note: Date and Day cannot be edited to keep the timeline consistent.

        Args:
            row_index:   The 0-based position of the row to edit.
            category:    New category value (leave None to keep existing).
            description: New description (leave None to keep existing).
            amount:      New amount — must be a positive number (leave None to keep existing).
            notes:       New notes (leave None to keep existing).
            csv_file:    (Optional) path to a custom CSV file.

        Returns:
            The original and updated versions of the expense record.
        """
        csv_path = self._resolve_csv_path(csv_file)
        df = self._load_expenses(csv_path)

        if df.empty:
            return self._build_error("No expenses found in the file.")

        if row_index < 0 or row_index >= len(df):
            return self._build_error(
                f"row_index {row_index} is out of range. "
                f"Valid range: 0 to {len(df) - 1}."
            )

        original = df.iloc[row_index].to_dict()

        if category is not None:
            safe = category.strip()
            if not safe:
                return self._build_error("Category cannot be empty.")
            df.at[row_index, "Category"] = safe

        if description is not None:
            safe = description.strip()
            if not safe:
                return self._build_error("Description cannot be empty.")
            df.at[row_index, "Description"] = safe

        if amount is not None:
            try:
                safe_amount = float(amount)
            except (TypeError, ValueError):
                return self._build_error("Amount must be a number.")
            if safe_amount <= 0:
                return self._build_error("Amount must be greater than 0.")
            df.at[row_index, "Amount"] = safe_amount

        if notes is not None:
            df.at[row_index, "Notes"] = notes.strip()

        self._save_expenses(df, csv_path)
        updated = df.iloc[row_index].to_dict()

        return self._build_success(
            {
                "message": "Expense updated.",
                "original": original,
                "updated": updated,
                "csv_path": str(csv_path),
            }
        )

    def top_spending_days(
        self,
        start_date: str,
        end_date: str,
        top_n: int = 5,
        csv_file: str | None = None,
    ) -> dict[str, Any]:
        """Find the N days with the highest total spending within a date range.

        Great for spotting splurge days or anomalies in your spending pattern.

        Args:
            start_date: Start of the range in YYYY-MM-DD format (inclusive).
            end_date:   End of the range in YYYY-MM-DD format (inclusive).
            top_n:      How many top days to return (default: 5).
            csv_file:   (Optional) path to a custom CSV file.

        Returns:
            A ranked list of dates with their total spend and individual records.
        """
        try:
            start = self._parse_date(start_date)
            end = self._parse_date(end_date)
        except ValueError:
            return self._build_error("Invalid date format. Expected YYYY-MM-DD.")

        if end < start:
            return self._build_error("end_date must be on or after start_date.")

        if top_n < 1:
            return self._build_error("top_n must be at least 1.")

        csv_path = self._resolve_csv_path(csv_file)
        df = self._load_expenses(csv_path)

        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        mask = (df["Date"] >= pd.Timestamp(start)) & (df["Date"] <= pd.Timestamp(end))
        filtered = df[mask].copy()

        if filtered.empty:
            return self._build_success(
                {"top_days": [], "csv_path": str(csv_path)}
            )

        daily_totals = (
            filtered.groupby(filtered["Date"].dt.strftime("%Y-%m-%d"))["Amount"]
            .sum()
            .sort_values(ascending=False)
            .head(top_n)
        )

        top_days = []
        for date_str, total in daily_totals.items():
            day_records = filtered[filtered["Date"].dt.strftime("%Y-%m-%d") == date_str]
            top_days.append(
                {
                    "date": date_str,
                    "day_of_week": day_records["Day"].iloc[0] if len(day_records) else "",
                    "total_amount": float(total),
                    "records": day_records.assign(Date=date_str).to_dict(orient="records"),
                }
            )

        return self._build_success(
            {
                "start_date": start_date,
                "end_date": end_date,
                "top_days": top_days,
                "csv_path": str(csv_path),
            }
        )

    def category_trend(
        self,
        category: str,
        year: int,
        csv_file: str | None = None,
    ) -> dict[str, Any]:
        """Show month-by-month spending for a single category across a whole year.

        Useful for spotting seasonal patterns or whether a habit is getting more
        or less expensive over time.

        Args:
            category: The category name to track (case-insensitive).
            year:     The 4-digit year to analyse, e.g. 2025.
            csv_file: (Optional) path to a custom CSV file.

        Returns:
            A list of 12 month entries with the spend for that category,
            plus the yearly total and the month with the highest spend.
        """
        if not category or not category.strip():
            return self._build_error("Category is required.")

        csv_path = self._resolve_csv_path(csv_file)
        df = self._load_expenses(csv_path)

        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        cat_mask = df["Category"].str.lower() == category.strip().lower()
        year_mask = df["Date"].dt.year == year
        filtered = df[cat_mask & year_mask].copy()

        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ]

        monthly: dict[int, float] = {m: 0.0 for m in range(1, 13)}
        if not filtered.empty:
            for month_num, total in filtered.groupby(filtered["Date"].dt.month)["Amount"].sum().items():
                monthly[int(month_num)] = float(total)

        trend = [
            {"month": month_names[m - 1], "month_number": m, "amount": monthly[m]}
            for m in range(1, 13)
        ]

        yearly_total = sum(monthly.values())
        peak_month_num = max(monthly, key=lambda m: monthly[m])

        return self._build_success(
            {
                "category": category.strip(),
                "year": year,
                "monthly_trend": trend,
                "yearly_total": yearly_total,
                "peak_month": month_names[peak_month_num - 1],
                "peak_amount": monthly[peak_month_num],
                "csv_path": str(csv_path),
            }
        )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

expense_tools = ExpenseTools()


# ---------------------------------------------------------------------------
# Original convenience functions
# ---------------------------------------------------------------------------

def add_daily_expense(
    date: str,
    category: str,
    description: str,
    amount: float,
    notes: str = "",
    csv_file: str | None = None,
) -> dict[str, Any]:
    """Add one expense record. See ExpenseTools.add_daily_expense for full docs."""
    return expense_tools.add_daily_expense(
        date=date,
        category=category,
        description=description,
        amount=amount,
        notes=notes,
        csv_file=csv_file,
    )


def monthly_category_expense(
    year: int,
    month: int,
    csv_file: str | None = None,
) -> dict[str, Any]:
    """Get category totals for a given month. See ExpenseTools.monthly_category_expense."""
    return expense_tools.monthly_category_expense(
        year=year,
        month=month,
        csv_file=csv_file,
    )


def weekly_category_expense(
    year: int,
    week: int,
    csv_file: str | None = None,
) -> dict[str, Any]:
    """Get category totals for a given ISO week. See ExpenseTools.weekly_category_expense."""
    return expense_tools.weekly_category_expense(
        year=year,
        week=week,
        csv_file=csv_file,
    )


# ---------------------------------------------------------------------------
# New convenience functions
# ---------------------------------------------------------------------------

def get_expense_summary(
    start_date: str,
    end_date: str,
    csv_file: str | None = None,
) -> dict[str, Any]:
    """Total spending + category breakdown for any custom date range.
    See ExpenseTools.get_expense_summary for full docs."""
    return expense_tools.get_expense_summary(
        start_date=start_date,
        end_date=end_date,
        csv_file=csv_file,
    )


def search_expenses(
    keyword: str | None = None,
    category: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    csv_file: str | None = None,
) -> dict[str, Any]:
    """Search expenses with flexible filters. See ExpenseTools.search_expenses for full docs."""
    return expense_tools.search_expenses(
        keyword=keyword,
        category=category,
        start_date=start_date,
        end_date=end_date,
        min_amount=min_amount,
        max_amount=max_amount,
        csv_file=csv_file,
    )


def delete_expense(
    row_index: int,
    csv_file: str | None = None,
) -> dict[str, Any]:
    """Delete an expense by its 0-based row index. See ExpenseTools.delete_expense for full docs."""
    return expense_tools.delete_expense(
        row_index=row_index,
        csv_file=csv_file,
    )


def edit_expense(
    row_index: int,
    category: str | None = None,
    description: str | None = None,
    amount: float | None = None,
    notes: str | None = None,
    csv_file: str | None = None,
) -> dict[str, Any]:
    """Edit one or more fields of an existing expense. See ExpenseTools.edit_expense for full docs."""
    return expense_tools.edit_expense(
        row_index=row_index,
        category=category,
        description=description,
        amount=amount,
        notes=notes,
        csv_file=csv_file,
    )


def top_spending_days(
    start_date: str,
    end_date: str,
    top_n: int = 5,
    csv_file: str | None = None,
) -> dict[str, Any]:
    """Find the N days with the highest spend in a date range. See ExpenseTools.top_spending_days."""
    return expense_tools.top_spending_days(
        start_date=start_date,
        end_date=end_date,
        top_n=top_n,
        csv_file=csv_file,
    )


def category_trend(
    category: str,
    year: int,
    csv_file: str | None = None,
) -> dict[str, Any]:
    """Month-by-month spend for one category across a year. See ExpenseTools.category_trend."""
    return expense_tools.category_trend(
        category=category,
        year=year,
        csv_file=csv_file,
    )


# ---------------------------------------------------------------------------
# Quick smoke-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Original tools
    result = add_daily_expense(
        date="2024-06-01",
        category="Food",
        description="Lunch at cafe",
        amount=12.50,
        notes="Had a sandwich and coffee",
    )
    print("add_daily_expense →", result)

    res2 = weekly_category_expense(year=2026, week=11)
    print("weekly_category_expense →", res2)

    # New tools
    print("\n--- New tools ---")

    summary = get_expense_summary(start_date="2024-01-01", end_date="2024-12-31")
    print("get_expense_summary →", summary)

    found = search_expenses(keyword="cafe", min_amount=10)
    print("search_expenses →", found)

    trend = category_trend(category="Food", year=2024)
    print("category_trend →", trend)

    top = top_spending_days(start_date="2024-01-01", end_date="2024-12-31", top_n=3)
    print("top_spending_days →", top)