from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


from src.agents.jobSearcher import root_agent as job_agent
from src.agents.calenderManager import root_agent as calendar_agent
from src.agents.expenseManager import root_agent as expense_agent
from src.agents.browserSearcher import root_agent as browser_agent
from src.services.llm_services import LLMServices
import datetime

APP_NAME = "wingman_orchestrator"

# Initialize orchestrator model using centralized LLM service
orchestrator_model = LLMServices().get_model()

orchestrator = LlmAgent(
    name=APP_NAME,
    model=orchestrator_model,
    instruction=(
        "You are Wingman's orchestrator. "
        "Your job is to analyze each user request, decide which specialist agent should handle it, "
        "and delegate to the best matching sub-agent.\n\n"
        "Reasoning rules:\n"
        "1. First identify the primary user intent: calendar, expense, job search, browser inspection, or mixed.\n"
        "2. If the request clearly belongs to one domain, delegate to exactly one sub-agent.\n"
        "3. If the request combines domains, delegate in the minimum sequence needed to complete it.\n"
        "4. If important information is missing, ask one concise clarifying question.\n"
        "5. Do not invent calendar events, expenses, or job data yourself; rely on sub-agents.\n"
        "6. Preserve explicit dates, times, companies, locations, and amounts from the user request.\n"
        "7. If the user says 'latest', 'today', 'tomorrow', or similar, interpret it using the current date.\n"
        "8. Prefer concise final answers and avoid unnecessary explanations.\n\n"
        "9. If the user asks to inspect a browser page, capture HTML, inspect DOM, or work with buttons/forms on a live page, delegate to the browser inspection agent.\n"
        "10. If you find that the user's request needs to be completed by using multiple agents, you should call the agents and complete it in the same conversation."
        f"Today's date is {datetime.datetime.now().strftime('%Y-%m-%d')}."
    ),
    description=(
        "Main orchestrator agent for Wingman that delegates user queries to the "
        "appropriate sub-agent."
    ),
    sub_agents=[job_agent, calendar_agent, expense_agent, browser_agent],
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
