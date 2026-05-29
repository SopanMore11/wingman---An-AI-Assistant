from src.agents.base_agent import BaseAgent
from src.tools.browser_query_tools import (
    capture_current_browser_page_html,
    list_browser_pages,
    open_url_and_capture_html,
    open_url_and_capture_html_with_local_browser,
)
from src.utils import load_md_file


class BrowserSearchAgent(BaseAgent):
    """Agent for inspecting browser pages and returning HTML content."""

    def __init__(self):
        super().__init__(
            name="browser_search_agent",
            description=(
                "Inspects browser pages for the user's query and returns cleaned HTML "
                "content, visible text, and page metadata."
            ),
            instruction=load_md_file("skills/browser_search.md"),
        )

    def _get_tools(self):
        return [
            list_browser_pages,
            capture_current_browser_page_html,
            open_url_and_capture_html,
            open_url_and_capture_html_with_local_browser,
        ]


root_agent = BrowserSearchAgent().agent

if __name__ == "__main__":
    BrowserSearchAgent().chat_cli()
