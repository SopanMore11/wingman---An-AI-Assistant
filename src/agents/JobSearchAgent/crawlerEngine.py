import requests
import time
import json
import csv
import os
from datetime import datetime, timezone

# ==========================
# CONFIG
# ==========================
BASE_URL = "https://jpmc.fa.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/jobs",
    "Origin": "https://jpmc.fa.oraclecloud.com",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}

SITE_NUMBER       = "CX_1001"
INDIA_LOCATION_ID = "300000000289360"
AI_CATEGORY_ID    = "300000086152753"   # "AI" category facet — from your network tab
PAGE_SIZE         = 25

# Facets copied verbatim from your request URL
FACETS_LIST = "LOCATIONS;WORK_LOCATIONS;WORKPLACE_TYPES;TITLES;CATEGORIES;ORGANIZATIONS;POSTING_DATES;FLEX_FIELDS"

# Expand fields copied verbatim from your request URL
EXPAND_FIELDS = (
    "requisitionList.workLocation,"
    "requisitionList.otherWorkLocations,"
    "requisitionList.secondaryLocations,"
    "flexFieldsFacet.values,"
    "requisitionList.requisitionFlexFields"
)

# Each keyword is searched separately to maximise result coverage
# (Oracle HCM caps results per search, so multi-keyword sweeps help)
AI_KEYWORDS = [
    "AI",
    "machine learning",
    "LLM",
    "generative AI",
    "data science",
    "NLP",
    "deep learning",
    "MLOps",
]

OUTPUT_JSON = "dataset/jpmc_ai_jobs_india.json"
OUTPUT_CSV  = "dataset/jpmc_ai_jobs_india.csv"

# ==========================
# HELPERS
# ==========================

def build_finder(keyword: str, offset: int) -> str:
    """
    Reconstruct the finder string exactly as seen in the browser network tab.
    Note: requests will percent-encode this value as a whole; the semicolons
    inside are the Oracle HCM parameter delimiter and must NOT be pre-encoded.
    """
    return (
        f"findReqs;"
        f"siteNumber={SITE_NUMBER},"
        f'facetsList={FACETS_LIST},'
        f"limit={PAGE_SIZE},"
        f"offset={offset},"
        f'keyword="{keyword}",'
        f"lastSelectedFacet=CATEGORIES,"
        f"locationId={INDIA_LOCATION_ID},"
        f"selectedCategoriesFacet={AI_CATEGORY_ID},"
        f"sortBy=RELEVANCY"
    )

def build_apply_url(job_id) -> str:
    return (
        f"https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en"
        f"/sites/{SITE_NUMBER}/job/{job_id}"
    )

def extract_location_name(loc) -> str:
    """Safely extract Name whether the API returns a dict or a list of dicts."""
    if isinstance(loc, dict):
        return loc.get("Name", "")
    if isinstance(loc, list) and loc:
        first = loc[0]
        return first.get("Name", "") if isinstance(first, dict) else str(first)
    return ""

def extract_location_list(locs) -> list:
    """Normalise otherWorkLocations — could be a list of dicts or a plain list."""
    if not locs:
        return []
    if isinstance(locs, list):
        return [extract_location_name(l) for l in locs]
    return [extract_location_name(locs)]

def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()

def format_job(job: dict) -> dict:
    work_location = job.get("workLocation")
    other_locs    = job.get("otherWorkLocations")
    flex_fields   = job.get("requisitionFlexFields") or []
    flex = {
        f.get("FlexFieldNameCode"): f.get("FlexFieldValueCode")
        for f in flex_fields if isinstance(f, dict) and f.get("FlexFieldNameCode")
    }
    return {
        "id":               job.get("Id"),
        "title":            job.get("Title", ""),
        "primary_location": job.get("PrimaryLocation", ""),
        "work_location":    extract_location_name(work_location),
        "other_locations":  extract_location_list(other_locs),
        "workplace_type":   job.get("WorkplaceType", ""),
        "category":         job.get("CategoryName", ""),
        "organization":     job.get("OrganizationName", ""),
        "posted":           job.get("PostedDate", ""),
        "flex_fields":      flex,
        "apply_url":        build_apply_url(job.get("Id")),
        "scraped_at":       datetime.now(timezone.utc).isoformat(),
    }

# ==========================
# PERSISTENCE
# ==========================

def load_existing() -> dict:
    if not os.path.exists(OUTPUT_JSON):
        return {}
    with open(OUTPUT_JSON, "r") as f:
        jobs = json.load(f)
    print(f"Resumed: loaded {len(jobs)} previously saved jobs.")
    return {j["id"]: j for j in jobs}

def save_json(jobs_by_id: dict):
    with open(OUTPUT_JSON, "w") as f:
        json.dump(list(jobs_by_id.values()), f, indent=2)

def save_csv(jobs_by_id: dict):
    if not jobs_by_id:
        return
    rows = list(jobs_by_id.values())
    flat_rows = []
    for r in rows:
        flat = dict(r)
        flat["other_locations"] = "; ".join(r.get("other_locations") or [])
        flat["flex_fields"]     = json.dumps(r.get("flex_fields") or {})
        flat_rows.append(flat)
    fields = list(flat_rows[0].keys())
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(flat_rows)

def persist(jobs_by_id: dict):
    """Write full state to disk after every page — safe incremental save."""
    save_json(jobs_by_id)
    save_csv(jobs_by_id)

# ==========================
# CRAWLER
# ==========================

def fetch_page(keyword: str, offset: int) -> list | None:
    """Returns list of requisitions, [] if exhausted, None on hard error."""
    params = {
        "onlyData": "true",
        "expand":   EXPAND_FIELDS,
        "finder":   build_finder(keyword, offset),
    }
    try:
        resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=20)
    except requests.RequestException as e:
        print(f"    [!] Network error: {e}")
        return None

    if resp.status_code == 429:
        wait = int(resp.headers.get("Retry-After", 15))
        print(f"    [!] Rate limited — waiting {wait}s")
        time.sleep(wait)
        return fetch_page(keyword, offset)  # one retry

    if resp.status_code != 200:
        print(f"    [!] HTTP {resp.status_code}: {resp.text[:300]}")
        return None

    try:
        data = resp.json()
        return data["items"][0].get("requisitionList", [])
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"    [!] Parse error: {e}")
        return None


def crawl_keyword(keyword: str, jobs_by_id: dict) -> dict:
    offset    = 0
    page      = 1
    new_count = 0

    print(f'\n  Searching: "{keyword}"')

    while True:
        print(f"    Page {page:>3} | offset {offset:>5}", end=" → ")
        reqs = fetch_page(keyword, offset)

        if reqs is None:
            print("Error — skipping.")
            break
        if not reqs:
            print("No more results.")
            break

        new_on_page = 0
        for job in reqs:
            jid = job.get("Id")
            if jid and jid not in jobs_by_id:
                jobs_by_id[jid] = format_job(job)
                new_on_page += 1

        new_count += new_on_page
        print(f"{new_on_page} new  |  total saved: {len(jobs_by_id)}")

        # Save after every page so nothing is lost on crash
        persist(jobs_by_id)

        if len(reqs) < PAGE_SIZE:
            print("    Last page reached.")
            break

        offset += PAGE_SIZE
        page   += 1
        time.sleep(0.75)

    print(f'  Done: "{keyword}" — {new_count} new jobs added.')
    return jobs_by_id


# ==========================
# ENTRY POINT
# ==========================

if __name__ == "__main__":
    print("=" * 60)
    print("  JPMorgan AI/ML Jobs — India Crawler")
    print(f"  Location : {INDIA_LOCATION_ID}  |  Category : {AI_CATEGORY_ID}")
    print(f"  Started  : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    jobs_by_id = load_existing()

    for kw in AI_KEYWORDS:
        jobs_by_id = crawl_keyword(kw, jobs_by_id)
        time.sleep(1.5)  # pause between keyword sweeps

    print("\n" + "=" * 60)
    print(f"  TOTAL UNIQUE AI/ML India Jobs : {len(jobs_by_id)}")
    print(f"  JSON -> {OUTPUT_JSON}")
    print(f"  CSV  -> {OUTPUT_CSV}")
    print("=" * 60)

    print("\n── Most Recent Listings ──")
    for job in sorted(jobs_by_id.values(), key=lambda x: x["posted"], reverse=True)[:20]:
        print(f"\n[{job['posted'][:10]}] {job['title']}")
        print(f"  Location : {job['primary_location']}  |  {job['workplace_type']}")
        print(f"  Apply    : {job['apply_url']}")