from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from src.agents.JobSearchAgent.agent import root_agent as job_agent
from src.agents.calenderAgent.agent import root_agent as calendar_agent
from src.agents.expenseManagerAgent.agent import root_agent as expense_agent
from src.agents.calenderAgent.tools import get_current_datetime
from src.services.llm_services import LLMServices
import datetime

APP_NAME = "wingman_orchestrator"

groq_model = LLMServices().get_model(provider="groq")

orchestrator = LlmAgent(
    name=APP_NAME,
    model=groq_model,
    instruction=(
        "Route each user request to the best sub-agent for job search, calendar "
        "management, or expense tracking. Prefer delegating to exactly one "
        "sub-agent unless the user explicitly combines tasks."
    ),
    description=(
        "Main orchestrator agent for Wingman that delegates user queries to the "
        "appropriate sub-agent."
    ),
    sub_agents=[job_agent, calendar_agent, expense_agent],
)


class WingmanRuntime:
    def __init__(self) -> None:
        self.session_service = InMemorySessionService()
        self.runner = Runner(
            agent=orchestrator,
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
                    final_response_text = event.content.parts[0].text
                elif event.actions and event.actions.escalate:
                    final_response_text = (
                        f"Request escalated: {event.error_message or 'No specific details.'}"
                    )
                break

        return final_response_text