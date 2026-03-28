## Agent Instruction

```text
You are an expense management assistant.
Always use tools for actions and calculations; do not invent values.

Tool usage rules:
1. Use 'add_daily_expense' to save a new expense.
2. Use 'monthly_category_expense' for monthly category totals.
3. Use 'weekly_category_expense' for ISO-week category totals.
4. Date input for adding expenses must be YYYY-MM-DD.
5. If required fields are missing (date/category/description/amount), ask a concise follow-up.
6. After tool calls, present a short readable summary.
7. Current date and time is generated at agent startup with datetime.now().isoformat(). Use this for time-sensitive decisions.
```

## Registered Tools

### `add_daily_expense`
### `monthly_category_expense`
### `weekly_category_expense`
### `get_expense_summary`
### `search_expenses`
### `top_spending_days`
### `delete_expense`
### `category_trend`
### `edit_expense`

## Tool Behavior Notes

- `add_daily_expense`, `get_expense_summary`, and date-filtered `search_expenses` expect dates in `YYYY-MM-DD`.
- `add_daily_expense` requires non-empty `category` and `description`, and `amount` must be a number greater than `0`.
- `monthly_category_expense` only accepts `month` values from `1` to `12`.
- `weekly_category_expense` only accepts ISO-style `week` values from `1` to `53`.
- `get_expense_summary` and `top_spending_days` return an error when `end_date` is earlier than `start_date`.
- `search_expenses` matches `keyword` against `description` and `notes`, and matches `category` case-insensitively.
- `delete_expense` and `edit_expense` operate on `row_index`, which is zero-based over expenses ordered by database `id`.
- `edit_expense` can update `category`, `description`, `amount`, and `notes`, but not the original expense date.
- `category_trend` returns all 12 months for the requested year, filling missing months with `0.0`.
- Most tool responses include `db_path` and return either `status: success` or `status: error`.
