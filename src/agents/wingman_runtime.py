import re
from collections.abc import Iterable

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from src.services.llm_services import LLMServices
import datetime

APP_NAME = "wingman_orchestrator"


def _clean_response_text(text: str) -> str:
    """Remove tool-call markup that should never reach Telegram."""
    return re.sub(r"<tool_call>[\s\S]*?(?:</tool_call>|<tool_call>)", "", text).strip()


def _extract_final_response_text(parts: Iterable[types.Part]) -> str:
    """Prefer non-thought text parts and fall back only if needed."""
    visible_chunks: list[str] = []
    fallback_chunks: list[str] = []

    for part in parts:
        text = getattr(part, "text", None)
        if not text:
            continue

        cleaned_text = _clean_response_text(text)
        if not cleaned_text:
            continue

        if getattr(part, "thought", False):
            fallback_chunks.append(cleaned_text)
        else:
            visible_chunks.append(cleaned_text)

    if visible_chunks:
        return "\n".join(visible_chunks).strip()
    if fallback_chunks:
        return "\n".join(fallback_chunks).strip()
    return ""


def _build_orchestrator_instruction() -> str:
    return (
        "You are Wingman's orchestrator. "
        "Your job is to analyze each user request, decide which specialist agent should handle it, "
        "and delegate to the best matching sub-agent.\n\n"
        "Reasoning rules:\n"
        "1. First identify the primary user intent: calendar, expense, job search, internet search, browser inspection, or mixed.\n"
        "2. If the request clearly belongs to one domain, delegate to exactly one sub-agent.\n"
        "3. If the request combines domains, delegate in the minimum sequence needed to complete it.\n"
        "4. If important information is missing, ask one concise clarifying question.\n"
        "5. Do not invent calendar events, expenses, or job data yourself; rely on sub-agents.\n"
        "6. Preserve explicit dates, times, companies, locations, and amounts from the user request.\n"
        "7. If the user says 'latest', 'today', 'tomorrow', or similar, interpret it using the current date.\n"
        "8. Prefer concise final answers and avoid unnecessary explanations.\n\n"
        "9. If the user asks to search the internet, Google, news, images, videos, maps, places, reviews, shopping, Scholar, patents, autocomplete, or Lens, delegate to the browser search agent.\n"
        "10. If the user asks to inspect a browser page, capture HTML, inspect DOM, or work with buttons/forms on a live page, delegate to the browser search agent.\n"
        "11. If you find that the user's request needs to be completed by using multiple agents, you should call the agents and complete it in the same conversation.\n"
        "12. Final answers are sent to Telegram with HTML parse mode. Use Telegram-safe HTML, not Markdown. "
        "Never use Markdown headings, **bold**, or [text](url) links. Use <b>text</b> for bold and "
        "<a href=\"url\">text</a> for links. Escape literal <, >, and & as &lt;, &gt;, and &amp;.\n"
        f"Today's date is {datetime.datetime.now().strftime('%Y-%m-%d')}."
    )


def build_orchestrator() -> LlmAgent:
    from src.agents.browserSearcher import build_browser_agent
    from src.agents.calenderManager import build_calendar_agent
    from src.agents.expenseManager import build_expense_agent
    from src.agents.jobSearcher import build_job_agent

    orchestrator_model = LLMServices().get_model()

    return LlmAgent(
        name=APP_NAME,
        model=orchestrator_model,
        instruction=_build_orchestrator_instruction(),
        description=(
            "Main orchestrator agent for Wingman that delegates user queries to the "
            "appropriate sub-agent."
        ),
        sub_agents=[
            build_job_agent(),
            build_calendar_agent(),
            build_expense_agent(),
            build_browser_agent(),
        ],
    )


class WingmanRuntime:
    def __init__(self) -> None:
        self.session_service = InMemorySessionService()
        self.agent = build_orchestrator()
        self.runner = Runner(
            agent=self.agent,
            app_name=APP_NAME,
            session_service=self.session_service,
        )
        self._known_sessions: set[tuple[str, str]] = set()

    async def _ensure_session(self, user_id: str, session_id: str) -> None:
        key = (user_id, session_id)
        if key in self._known_sessions:
            return

        await self.session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )
        self._known_sessions.add(key)

    async def ask(self, user_id: str, session_id: str, text: str) -> str:
        await self._ensure_session(user_id=user_id, session_id=session_id)
        content = types.Content(role="user", parts=[types.Part(text=text)])
        final_response_text = "I couldn't generate a response. Please try again."

        async for event in self.runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    extracted_text = _extract_final_response_text(event.content.parts)
                    if extracted_text:
                        final_response_text = extracted_text
                elif event.actions and event.actions.escalate:
                    final_response_text = (
                        f"Request escalated: {event.error_message or 'No specific details.'}"
                    )

        return final_response_text
