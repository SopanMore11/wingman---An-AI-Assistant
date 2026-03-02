import os
from dotenv import load_dotenv
from google.adk.agents.llm_agent import Agent
from google.adk.models import LiteLlm

from .tools import (
    get_all_jobs,
    get_jobs_by_location,
    get_recent_jobs,
    get_jobs_by_posted_date_range,
    get_jobs_by_keyword,
    search_jobs,
    get_job_filter_metadata,
    extract_job_details_from_url,
)

# Load environment variables
load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

model = LiteLlm(
    model="groq/openai/gpt-oss-120b",
)

root_agent = Agent(
    # model="gemini-3-flash-preview",
    model = model,
    name="job_search_agent",
    description=(
        "Searches multi-company jobs from local JSON datasets using "
        "structured filters like location, recency, date range, and keyword."
    ),
    instruction="""
        You are a job search assistant for multiple companies (for example JPMC and Oracle).
        Always use tools to retrieve jobs; do not guess.
        Prefer precise filters and return concise summaries.

        Tool usage rules:
        1. Use 'get_job_filter_metadata' first when user asks available locations/categories/companies.
        2. Use 'get_jobs_by_location' for location-wise filtering.
        3. Use 'get_recent_jobs' for recently posted jobs (days-based).
        4. Use 'get_jobs_by_posted_date_range' for explicit date ranges.
        5. Use 'get_jobs_by_keyword' for role/skill/title keyword queries.
        6. Use 'search_jobs' when multiple filters are requested together, including company.
        7. Use 'get_all_jobs' only when user asks broad listings.
        8. Respect pagination (limit/offset) when the user asks for more results.
        9. If user mentions a company (e.g., Oracle), pass company=<name> to tools.
        10. If user provides a job link and asks for details, use 'extract_job_details_from_url'.
    """,
    tools=[
        get_all_jobs,
        get_jobs_by_location,
        get_recent_jobs,
        get_jobs_by_posted_date_range,
        get_jobs_by_keyword,
        search_jobs,
        get_job_filter_metadata,
        extract_job_details_from_url,
    ],
)

if __name__ == "__main__":
    root_agent.start()
