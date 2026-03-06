from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

JOB_APP_NAME = "wingman_jobs"
CALENDAR_APP_NAME = "wingman_calendar"

JOB_HINTS = {
    "job",
    "jobs",
    "role",
    "roles",
    "opening",
    "openings",
    "hiring",
    "apply",
    "career",
    "position",
    "positions",
    "vacancy",
    "vacancies",
}
CALENDAR_HINTS = {
    "calendar",
    "schedule",
    "event",
    "events",
    "meeting",
    "meetings",
    "free",
    "slot",
    "slots",
    "appointment",
    "appointments",
    "today",
    "tomorrow",
    "reschedule",
    "delete",
    "update",
}


class WingmanRuntime:
    def __init__(self) -> None:
        from src.agents.JobSearchAgent.agent import root_agent as job_agent
        from src.agents.calenderAgent.agent import root_agent as calendar_agent

        self.session_service = InMemorySessionService()
        self.job_runner = Runner(
            agent=job_agent,
            app_name=JOB_APP_NAME,
            session_service=self.session_service,
        )
        self.calendar_runner = Runner(
            agent=calendar_agent,
            app_name=CALENDAR_APP_NAME,
            session_service=self.session_service,
        )
        self._known_sessions: set[tuple[str, str, str]] = set()

    async def _ensure_session(self, app_name: str, user_id: str, session_id: str) -> None:
        key = (app_name, user_id, session_id)
        if key in self._known_sessions:
            return

        await self.session_service.create_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
        )
        self._known_sessions.add(key)

    @staticmethod
    def _route_query(text: str) -> str:
        lowered = text.lower()
        job_score = sum(1 for hint in JOB_HINTS if hint in lowered)
        calendar_score = sum(1 for hint in CALENDAR_HINTS if hint in lowered)
        return "jobs" if job_score > calendar_score else "calendar"

    async def _ask_runner(self, runner: Runner, app_name: str, user_id: str, session_id: str, text: str) -> str:
        await self._ensure_session(app_name=app_name, user_id=user_id, session_id=session_id)
        content = types.Content(role="user", parts=[types.Part(text=text)])
        final_response_text = "I couldn't generate a response. Please try again."

        async for event in runner.run_async(
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

    async def ask(self, user_id: str, session_id: str, text: str) -> str:
        route = self._route_query(text)
        if route == "jobs":
            return await self._ask_runner(
                runner=self.job_runner,
                app_name=JOB_APP_NAME,
                user_id=user_id,
                session_id=f"{session_id}_jobs",
                text=text,
            )
        return await self._ask_runner(
            runner=self.calendar_runner,
            app_name=CALENDAR_APP_NAME,
            user_id=user_id,
            session_id=f"{session_id}_calendar",
            text=text,
        )
