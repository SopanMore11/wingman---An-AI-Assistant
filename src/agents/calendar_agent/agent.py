import os
import datetime
from dotenv import load_dotenv
from src.agents.base_agent import BaseAgent
from src.google_authenticator import authenticate_google_calendar
from .tools import (
    get_current_datetime,
    get_schedule_for_date,
    create_calendar_event,
    delete_calendar_event,
    update_calendar_event,
    get_free_slots_for_date,
)

# Load environment variables
load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")


# Initialize Calendar Service
service = authenticate_google_calendar()


class CalendarAgent(BaseAgent):
    """Agent for managing Google Calendar events and schedules."""

    def __init__(self):
        super().__init__(
            name="root_agent",
            description="Manages and describes the user's calendar schedule in India Standard Time.",
            instruction="""
        Use 'get_current_datetime' to orient yourself to the user's current time.
        1. When asked about a schedule, always use 'get_schedule_for_date'. 
        2. Ensure the date is strictly in YYYY-MM-DD format.
        3. To add an event, use 'create_calendar_event'. 
        5. To delete an event for a date, use 'delete_calendar_event_for_date'.
        7. To update an event for a date, use 'update_calendar_event_for_date'.
        8. To find free time on a date, use 'get_free_slots_for_date'.
        4. IMPORTANT: All times are in India Standard Time (IST). Do not append 'Z' to timestamps.
        6. Summarize the day's flow (e.g., 'You have a free morning before your 2 PM meeting').
    """,
        )

    def _get_tools(self):
        """Return the list of tools available to this agent."""
        return [
            get_current_datetime,
            get_schedule_for_date,
            create_calendar_event,
            delete_calendar_event,
            update_calendar_event,
            get_free_slots_for_date,
        ]


# Export the agent instance
root_agent = CalendarAgent().agent

if __name__ == "__main__":
    # When run directly, start the agent. Importing this module won't auto-start it.
    root_agent.start()
