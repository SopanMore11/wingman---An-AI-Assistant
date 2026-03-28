from __future__ import annotations

from datetime import datetime
from typing import Any

from src.data.sqlite_store import get_connection, initialize_database


class ExpenseTools:
    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        return datetime.strptime(date_str, "%Y-%m-%d")

    @staticmethod
    def _build_success(data: dict[str, Any]) -> dict[str, Any]:
        return {"status": "success", **data}

    @staticmethod
    def _build_error(message: str) -> dict[str, Any]:
        return {"status": "error", "message": message}

    @staticmethod
    def _row_to_record(row: Any, row_index: int | None = None) -> dict[str, Any]:
        record = {
            "Date": row["expense_date"],
            "Day": row["day"],
            "Category": row["category"],
            "Description": row["description"],
            "Amount": float(row["amount"]),
            "Notes": row["notes"],
        }
        if row_index is not None:
            record["row_index"] = row_index
        return record

    @staticmethod
    def _resolve_db_path(_: str | None = None) -> str:
        return str(initialize_database())

    def add_daily_expense(
        self,
        date: str,
        category: str,
        description: str,
        amount: float,
        notes: str = "",
        csv_file: str | None = None,
    ) -> dict[str, Any]:
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

        db_path = self._resolve_db_path(csv_file)
        new_row = {
            "Date": parsed_date.strftime("%Y-%m-%d"),
            "Day": parsed_date.strftime("%A"),
            "Category": safe_category,
            "Description": safe_description,
            "Amount": safe_amount,
            "Notes": safe_notes,
        }

        with get_connection(db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO expenses (expense_date, day, category, description, amount, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    new_row["Date"],
                    new_row["Day"],
                    new_row["Category"],
                    new_row["Description"],
                    new_row["Amount"],
                    new_row["Notes"],
                ),
            )
            total_records = conn.execute("SELECT COUNT(*) AS count FROM expenses").fetchone()["count"]
            inserted_id = cursor.lastrowid
            order_row = conn.execute(
                "SELECT COUNT(*) AS count FROM expenses WHERE id <= ?",
                (inserted_id,),
            ).fetchone()
            row_index = int(order_row["count"]) - 1 if order_row else 0

        return self._build_success(
            {
                "message": "Expense added.",
                "expense": {**new_row, "row_index": row_index},
                "total_records": int(total_records),
                "db_path": db_path,
            }
        )

    def monthly_category_expense(
        self,
        year: int,
        month: int,
        csv_file: str | None = None,
    ) -> dict[str, Any]:
        if month < 1 or month > 12:
            return self._build_error("Month must be between 1 and 12.")

        db_path = self._resolve_db_path(csv_file)
        with get_connection(db_path) as conn:
            rows = conn.execute(
                """
                SELECT category, SUM(amount) AS total_amount
                FROM expenses
                WHERE strftime('%Y', expense_date) = ?
                  AND strftime('%m', expense_date) = ?
                GROUP BY category
                ORDER BY total_amount DESC, category ASC
                """,
                (f"{year:04d}", f"{month:02d}"),
            ).fetchall()

        totals = {str(row["category"]): float(row["total_amount"]) for row in rows}
        return self._build_success(
            {
                "year": year,
                "month": month,
                "category_totals": totals,
                "db_path": db_path,
            }
        )

    def weekly_category_expense(
        self,
        year: int,
        week: int,
        csv_file: str | None = None,
    ) -> dict[str, Any]:
        if week < 1 or week > 53:
            return self._build_error("Week must be between 1 and 53.")

        db_path = self._resolve_db_path(csv_file)
        with get_connection(db_path) as conn:
            rows = conn.execute(
                """
                SELECT category, SUM(amount) AS total_amount
                FROM expenses
                WHERE strftime('%Y', date(expense_date, '-3 days', 'weekday 4')) = ?
                  AND printf('%02d', CAST(strftime('%W', date(expense_date, '-3 days', 'weekday 4')) AS INTEGER) + 1) = ?
                GROUP BY category
                ORDER BY total_amount DESC, category ASC
                """,
                (f"{year:04d}", f"{week:02d}"),
            ).fetchall()

        totals = {str(row["category"]): float(row["total_amount"]) for row in rows}
        return self._build_success(
            {
                "year": year,
                "week": week,
                "category_totals": totals,
                "db_path": db_path,
            }
        )

    def get_expense_summary(
        self,
        start_date: str,
        end_date: str,
        csv_file: str | None = None,
    ) -> dict[str, Any]:
        try:
            start = self._parse_date(start_date)
            end = self._parse_date(end_date)
        except ValueError:
            return self._build_error("Invalid date format. Expected YYYY-MM-DD.")

        if end < start:
            return self._build_error("end_date must be on or after start_date.")

        db_path = self._resolve_db_path(csv_file)
        with get_connection(db_path) as conn:
            summary_row = conn.execute(
                """
                SELECT COALESCE(SUM(amount), 0) AS total_amount, COUNT(*) AS record_count
                FROM expenses
                WHERE expense_date BETWEEN ? AND ?
                """,
                (start_date, end_date),
            ).fetchone()
            category_rows = conn.execute(
                """
                SELECT category, SUM(amount) AS total_amount
                FROM expenses
                WHERE expense_date BETWEEN ? AND ?
                GROUP BY category
                ORDER BY total_amount DESC, category ASC
                """,
                (start_date, end_date),
            ).fetchall()

        return self._build_success(
            {
                "start_date": start_date,
                "end_date": end_date,
                "total_amount": float(summary_row["total_amount"]),
                "record_count": int(summary_row["record_count"]),
                "category_totals": {
                    str(row["category"]): float(row["total_amount"])
                    for row in category_rows
                },
                "db_path": db_path,
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
        if start_date:
            try:
                self._parse_date(start_date)
            except ValueError:
                return self._build_error("Invalid start_date format. Expected YYYY-MM-DD.")

        if end_date:
            try:
                self._parse_date(end_date)
            except ValueError:
                return self._build_error("Invalid end_date format. Expected YYYY-MM-DD.")

        db_path = self._resolve_db_path(csv_file)
        query = """
            SELECT
                id,
                expense_date,
                day,
                category,
                description,
                amount,
                notes,
                ROW_NUMBER() OVER (ORDER BY id) - 1 AS row_index
            FROM expenses
            WHERE 1 = 1
        """
        params: list[Any] = []

        if keyword:
            query += " AND (LOWER(description) LIKE ? OR LOWER(notes) LIKE ?)"
            pattern = f"%{keyword.strip().lower()}%"
            params.extend([pattern, pattern])

        if category:
            query += " AND LOWER(category) = ?"
            params.append(category.strip().lower())

        if start_date:
            query += " AND expense_date >= ?"
            params.append(start_date)

        if end_date:
            query += " AND expense_date <= ?"
            params.append(end_date)

        if min_amount is not None:
            query += " AND amount >= ?"
            params.append(min_amount)

        if max_amount is not None:
            query += " AND amount <= ?"
            params.append(max_amount)

        query += " ORDER BY id"

        with get_connection(db_path) as conn:
            rows = conn.execute(query, params).fetchall()

        matches = [
            self._row_to_record(row, row_index=int(row["row_index"]))
            for row in rows
        ]

        return self._build_success(
            {
                "matches": matches,
                "count": len(matches),
                "db_path": db_path,
            }
        )

    def delete_expense(
        self,
        row_index: int,
        csv_file: str | None = None,
    ) -> dict[str, Any]:
        db_path = self._resolve_db_path(csv_file)
        with get_connection(db_path) as conn:
            row = conn.execute(
                """
                SELECT id, expense_date, day, category, description, amount, notes
                FROM expenses
                ORDER BY id
                LIMIT 1 OFFSET ?
                """,
                (row_index,),
            ).fetchone()

            total_row = conn.execute("SELECT COUNT(*) AS count FROM expenses").fetchone()
            total_records = int(total_row["count"]) if total_row else 0

            if total_records == 0:
                return self._build_error("No expenses found in the database.")

            if row is None:
                return self._build_error(
                    f"row_index {row_index} is out of range. Valid range: 0 to {total_records - 1}."
                )

            conn.execute("DELETE FROM expenses WHERE id = ?", (row["id"],))
            remaining_records = conn.execute("SELECT COUNT(*) AS count FROM expenses").fetchone()["count"]

        deleted_expense = self._row_to_record(row, row_index=row_index)
        return self._build_success(
            {
                "message": "Expense deleted.",
                "deleted_expense": deleted_expense,
                "remaining_records": int(remaining_records),
                "db_path": db_path,
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
        db_path = self._resolve_db_path(csv_file)
        with get_connection(db_path) as conn:
            row = conn.execute(
                """
                SELECT id, expense_date, day, category, description, amount, notes
                FROM expenses
                ORDER BY id
                LIMIT 1 OFFSET ?
                """,
                (row_index,),
            ).fetchone()

            total_row = conn.execute("SELECT COUNT(*) AS count FROM expenses").fetchone()
            total_records = int(total_row["count"]) if total_row else 0

            if total_records == 0:
                return self._build_error("No expenses found in the database.")

            if row is None:
                return self._build_error(
                    f"row_index {row_index} is out of range. Valid range: 0 to {total_records - 1}."
                )

            updates: dict[str, Any] = {}
            if category is not None:
                safe = category.strip()
                if not safe:
                    return self._build_error("Category cannot be empty.")
                updates["category"] = safe

            if description is not None:
                safe = description.strip()
                if not safe:
                    return self._build_error("Description cannot be empty.")
                updates["description"] = safe

            if amount is not None:
                try:
                    safe_amount = float(amount)
                except (TypeError, ValueError):
                    return self._build_error("Amount must be a number.")
                if safe_amount <= 0:
                    return self._build_error("Amount must be greater than 0.")
                updates["amount"] = safe_amount

            if notes is not None:
                updates["notes"] = notes.strip()

            original = self._row_to_record(row, row_index=row_index)

            if updates:
                assignments = ", ".join(f"{column} = ?" for column in updates)
                params = list(updates.values()) + [row["id"]]
                conn.execute(f"UPDATE expenses SET {assignments} WHERE id = ?", params)

            updated_row = conn.execute(
                """
                SELECT id, expense_date, day, category, description, amount, notes
                FROM expenses
                WHERE id = ?
                """,
                (row["id"],),
            ).fetchone()

        updated = self._row_to_record(updated_row, row_index=row_index)
        return self._build_success(
            {
                "message": "Expense updated.",
                "original": original,
                "updated": updated,
                "db_path": db_path,
            }
        )

    def top_spending_days(
        self,
        start_date: str,
        end_date: str,
        top_n: int = 5,
        csv_file: str | None = None,
    ) -> dict[str, Any]:
        try:
            start = self._parse_date(start_date)
            end = self._parse_date(end_date)
        except ValueError:
            return self._build_error("Invalid date format. Expected YYYY-MM-DD.")

        if end < start:
            return self._build_error("end_date must be on or after start_date.")

        if top_n < 1:
            return self._build_error("top_n must be at least 1.")

        db_path = self._resolve_db_path(csv_file)
        with get_connection(db_path) as conn:
            top_days = conn.execute(
                """
                SELECT expense_date, day, SUM(amount) AS total_amount
                FROM expenses
                WHERE expense_date BETWEEN ? AND ?
                GROUP BY expense_date, day
                ORDER BY total_amount DESC, expense_date ASC
                LIMIT ?
                """,
                (start_date, end_date, top_n),
            ).fetchall()

            result = []
            for top_day in top_days:
                records = conn.execute(
                    """
                    SELECT
                        expense_date,
                        day,
                        category,
                        description,
                        amount,
                        notes,
                        ROW_NUMBER() OVER (ORDER BY id) - 1 AS row_index
                    FROM expenses
                    WHERE expense_date = ?
                    ORDER BY id
                    """,
                    (top_day["expense_date"],),
                ).fetchall()
                result.append(
                    {
                        "date": top_day["expense_date"],
                        "day_of_week": top_day["day"],
                        "total_amount": float(top_day["total_amount"]),
                        "records": [
                            self._row_to_record(record, row_index=int(record["row_index"]))
                            for record in records
                        ],
                    }
                )

        return self._build_success(
            {
                "start_date": start_date,
                "end_date": end_date,
                "top_days": result,
                "db_path": db_path,
            }
        )

    def category_trend(
        self,
        category: str,
        year: int,
        csv_file: str | None = None,
    ) -> dict[str, Any]:
        if not category or not category.strip():
            return self._build_error("Category is required.")

        db_path = self._resolve_db_path(csv_file)
        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ]

        with get_connection(db_path) as conn:
            rows = conn.execute(
                """
                SELECT CAST(strftime('%m', expense_date) AS INTEGER) AS month_number,
                       SUM(amount) AS total_amount
                FROM expenses
                WHERE LOWER(category) = ?
                  AND strftime('%Y', expense_date) = ?
                GROUP BY strftime('%m', expense_date)
                ORDER BY month_number
                """,
                (category.strip().lower(), f"{year:04d}"),
            ).fetchall()

        monthly = {month: 0.0 for month in range(1, 13)}
        for row in rows:
            monthly[int(row["month_number"])] = float(row["total_amount"])

        trend = [
            {"month": month_names[month - 1], "month_number": month, "amount": monthly[month]}
            for month in range(1, 13)
        ]

        yearly_total = sum(monthly.values())
        peak_month_num = max(monthly, key=lambda month: monthly[month])

        return self._build_success(
            {
                "category": category.strip(),
                "year": year,
                "monthly_trend": trend,
                "yearly_total": yearly_total,
                "peak_month": month_names[peak_month_num - 1],
                "peak_amount": monthly[peak_month_num],
                "db_path": db_path,
            }
        )
    
expense_tools = ExpenseTools()


def add_daily_expense(
    date: str,
    category: str,
    description: str,
    amount: float,
    notes: str = "",
    csv_file: str | None = None,
) -> dict[str, Any]:
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
    return expense_tools.monthly_category_expense(year=year, month=month, csv_file=csv_file)


def weekly_category_expense(
    year: int,
    week: int,
    csv_file: str | None = None,
) -> dict[str, Any]:
    return expense_tools.weekly_category_expense(year=year, week=week, csv_file=csv_file)


def get_expense_summary(
    start_date: str,
    end_date: str,
    csv_file: str | None = None,
) -> dict[str, Any]:
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
    return expense_tools.delete_expense(row_index=row_index, csv_file=csv_file)


def edit_expense(
    row_index: int,
    category: str | None = None,
    description: str | None = None,
    amount: float | None = None,
    notes: str | None = None,
    csv_file: str | None = None,
) -> dict[str, Any]:
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
    return expense_tools.category_trend(category=category, year=year, csv_file=csv_file)