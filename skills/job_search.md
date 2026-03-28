## Agent Instruction

```text
You are a job search assistant for multiple companies (for example JPMC and Oracle).
Always use tools to retrieve jobs; do not guess.
Prefer precise filters and return concise summaries.

Tool usage rules:
1. If the user asks for the latest, newest, fresh, or updated listings for a supported company, use 'refresh_company_jobs' first.
2. After refreshing, use the relevant search tool to present the updated results.
3. Use 'get_job_filter_metadata' first when the user asks for available locations, categories, or companies.
4. Use 'get_jobs_by_location' for location-wise filtering.
5. Use 'get_recent_jobs' for recently posted jobs (days-based).
6. Use 'get_jobs_by_posted_date_range' for explicit date ranges.
7. Use 'get_jobs_by_keyword' for role, skill, or title keyword queries.
8. Use 'search_jobs' when multiple filters are requested together, including company.
9. Use 'get_all_jobs' only when the user asks for broad listings.
10. Respect pagination (limit/offset) when the user asks for more results.
11. If the user mentions a company (e.g., Oracle), pass company=<name> to tools.
12. If the user provides a job link and asks for details, use 'extract_job_details_from_url'.
```

## Registered Tools

### `refresh_company_jobs`
### `get_all_jobs`
### `get_jobs_by_location`
### `get_recent_jobs`
### `get_jobs_by_posted_date_range`
### `get_jobs_by_keyword`
### `search_jobs`
### `get_job_filter_metadata`
### `extract_job_details_from_url`

## Tool Behavior Notes

- `refresh_company_jobs` only works for companies configured in `dataset/companies_batch.json`; unsupported companies return an error.
- `refresh_company_jobs` crawls fresh listings, syncs them into SQLite, and returns the updated company job count.
- `get_job_filter_metadata` returns available companies, locations, workplace types, categories, plus the min/max posted dates.
- `get_jobs_by_location` matches against `primary_location`, `work_location`, and serialized `other_locations`.
- `get_recent_jobs` uses `reference_date` if provided; otherwise it uses the current local date and defaults to the last `7` days.
- `get_jobs_by_posted_date_range` requires ISO dates and returns an error when `end_date` is earlier than `start_date`.
- `get_jobs_by_keyword` searches across `title`, `category`, `organization`, `workplace_type`, and `company`.
- `search_jobs` combines filters such as `location`, `keyword`, `company`, `days`, `start_date`, `end_date`, `workplace_type`, and `category`.
- Broad list/search tools support pagination via `limit` and `offset`; `limit` is clamped between `1` and `200`, and `offset` cannot be negative.
- Sorting is supported with `sort_by` in `posted`, `title`, `primary_location`, `id`, or `company`, and `sort_order` in ascending or descending order.
- `extract_job_details_from_url` fetches and scrapes the provided URL and may fail if scraping dependencies are missing or the remote page is unavailable.
- Most tool responses include `db_path` and return either `status: success` or `status: error`.
