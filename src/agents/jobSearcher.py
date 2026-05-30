from src.agents.base_agent import BaseAgent
from src.utils import load_md_file
from src.tools.job_search_tools import (
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


class JobSearchAgent(BaseAgent):
    """Agent for searching and retrieving jobs from local SQLite database."""

    def __init__(self):
        super().__init__(
            name="job_search_agent",
            description=(
                "Searches multi-company jobs from the local SQLite database using "
                "structured filters like location, recency, date range, and keyword."
            ),
            instruction=load_md_file("skills/job_search.md"),
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


def build_job_agent():
    return JobSearchAgent().agent
