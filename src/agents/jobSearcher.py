import os
from dotenv import load_dotenv
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


# Export the agent instance
root_agent = JobSearchAgent().agent

if __name__ == "__main__":
    JobSearchAgent().chat_cli()
