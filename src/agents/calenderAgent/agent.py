from google.adk.agents.llm_agent import Agent
from google_authenticator import authenticate_google_calendar
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

import datetime

service = authenticate_google_calendar()
def get_schedule_for_date(target_date_str):
    """
    Fetches all events for a specific date.
    :param target_date_str: A string in 'YYYY-MM-DD' format.
    """
    try:
        # 1. Create the start and end of the specific day in ISO format
        # We append 'Z' to indicate UTC, or you can use local offsets
        start_of_day = f"{target_date_str}T00:00:00Z"
        end_of_day = f"{target_date_str}T23:59:59Z"

        print(f"Fetching events for {target_date_str}...")

        # 2. Call the API with timeMin and timeMax
        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_of_day,
            timeMax=end_of_day,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        if not events:
            return f"No events found for {target_date_str}."

        # 3. Format the results
        output = f"Schedule for {target_date_str}:\n"
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            # Clean up the timestamp for better readability
            time_display = start.split('T')[1][:5] if 'T' in start else "All Day"
            summary = event.get('summary', 'No Title')
            output += f"[{time_display}] - {summary}\n"
            
        return output

    except Exception as e:
        return f"Error fetching schedule: {str(e)}"

def create_calendar_event(
    summary: str,
    description: str,
    start_datetime: str,
    end_datetime: str,
    timezone: str = "UTC",
):

    event = {
        "summary": summary,
        "description": description,
        "start": {
            "dateTime": start_datetime,
            "timeZone": timezone,
        },
        "end": {
            "dateTime": end_datetime,
            "timeZone": timezone,
        },
    }

    created_event = service.events().insert(
        calendarId="primary",
        body=event
    ).execute()

    return f"Event created: {created_event.get('htmlLink')}"


# --- Example Usage ---
# service = authenticate_google_calendar()
# print(get_schedule_for_date(service, "2024-10-25"))

root_agent = Agent(
    model='gemini-2.5-flash',
    name='root_agent',
    description="Manages and describes the user's calendar schedule for specific dates.",
    instruction="""
        1. When asked about a schedule, always use 'get_schedule_for_date'. 
        2. Ensure the date is strictly in YYYY-MM-DD format.
        3. If a user wants to add a meeting or event, use 'insert_calendar_event'. Confirm the details (summary, time, duration) before or after execution as appropriate.
        4. Be descriptive and helpful: Instead of just listing times, summarize the flow of the day (e.g., 'You have a busy morning with three back-to-back meetings...').
        5. If no events are found for a date, suggest available time slots for new events.
    """,
    tools=[get_schedule_for_date, create_calendar_event],
)