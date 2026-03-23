import os
from dotenv import load_dotenv
from src.agents.base_agent import BaseAgent
from .tools import (
    refresh_company_jobs,
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


class JobSearchAgent(BaseAgent):
    """Agent for searching and retrieving jobs from local SQLite database."""

    def __init__(self):
        super().__init__(
            name="job_search_agent",
            description=(
                "Searches multi-company jobs from the local SQLite database using "
                "structured filters like location, recency, date range, and keyword."
            ),
            instruction="""
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
    """,
        )

    def _get_tools(self):
        """Return the list of tools available to this agent."""
        return [
            refresh_company_jobs,
            get_all_jobs,
            get_jobs_by_location,
            get_recent_jobs,
            get_jobs_by_posted_date_range,
            get_jobs_by_keyword,
            search_jobs,
            get_job_filter_metadata,
            extract_job_details_from_url,
        ]


# Export the agent instance
root_agent = JobSearchAgent().agent

if __name__ == "__main__":
    root_agent.start()
