from src.agents.base_agent import BaseAgent
from src.utils import load_md_file
from src.tools.calender_tools import (
    get_current_datetime,
    get_schedule_for_date,
    create_calendar_event,
    delete_calendar_event,
    update_calendar_event,
    get_free_slots_for_date,
)


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


def build_calendar_agent():
    return CalendarAgent().agent
