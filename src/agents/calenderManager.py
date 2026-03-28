import os
import datetime
from dotenv import load_dotenv
from src.agents.base_agent import BaseAgent
from src.utils import load_md_file
from src.google_authenticator import authenticate_google_calendar
from src.tools.calender_tools import (
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
    def __init__(self):
        super().__init__(
            name="calendar_agent",
            description="Manages the user's calendar and schedule.",
            instruction=load_md_file("skills/calender.md"),
        )

    def _get_tools(self):
        return [
            get_current_datetime,
            get_schedule_for_date,
            create_calendar_event,
            delete_calendar_event,
            update_calendar_event,
            get_free_slots_for_date,
        ]


root_agent = CalendarAgent().agent

if __name__ == "__main__":
    # When run directly, start the agent. Importing this module won't auto-start it.
    root_agent.start()
