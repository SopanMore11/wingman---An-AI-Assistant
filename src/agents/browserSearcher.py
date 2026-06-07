from src.agents.base_agent import BaseAgent
from src.tools.browser_query_tools import (
    capture_current_browser_page_html,
    list_browser_pages,
    open_url_and_capture_html,
    open_url_and_capture_html_with_local_browser,
)
from src.tools.internet_tools import google_search
from src.utils import load_md_file


class BrowserSearchAgent(BaseAgent):
    """Agent for internet search and browser page inspection."""

    def __init__(self):
        super().__init__(
            name="browser_search_agent",
            description=(
                "Searches the internet with Serper and inspects browser pages, returning "
                "search results, cleaned HTML content, visible text, and page metadata."
            ),
            instruction=load_md_file("skills/browser_search.md"),
        )

    def _get_tools(self):
        return [
            list_browser_pages,
            capture_current_browser_page_html,
            open_url_and_capture_html,
            open_url_and_capture_html_with_local_browser,
            google_search,
        ]


def build_browser_agent():
    return BrowserSearchAgent().agent
