import os
import datetime
from dotenv import load_dotenv
from google.adk.agents.llm_agent import Agent
from google_authenticator import authenticate_google_calendar
from google.adk.models import LiteLlm

# Load environment variables
load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")


# Initialize Calendar Service
service = authenticate_google_calendar()

def get_schedule_for_date(target_date_str):
    """
    Fetches all events for a specific date in India Standard Time.
    :param target_date_str: A string in 'YYYY-MM-DD' format.
    """
    try:
        # Use +05:30 offset to ensure we fetch the correct day in India
        start_of_day = f"{target_date_str}T00:00:00+05:30"
        end_of_day = f"{target_date_str}T23:59:59+05:30"

        print(f"Fetching events for {target_date_str} (IST)...")

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

        output = f"Schedule for {target_date_str}:\n"
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            # Format time for display (extracts HH:MM)
            time_display = start.split('T')[1][:5] if 'T' in start else "All Day"
            summary = event.get('summary', 'No Title')
            output += f"[{time_display}] - {summary}\n"
            
        return output

    except Exception as e:
        return f"Error fetching schedule: {str(e)}"

def get_current_datetime():
    """Returns the current date and time in IST."""
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")

def create_calendar_event(
    summary: str,
    description: str,
    start_datetime: str,
    end_datetime: str,
    timezone: str = "Asia/Kolkata",
):
    """
    Creates a calendar event. 
    Accepts formats: 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DDTHH:MM:SS'
    """
    # 1. Clean up the format: Replace spaces with 'T' and remove 'Z' if present
    # We remove 'Z' because 'Z' forces UTC, which overrides the Asia/Kolkata setting.
    formatted_start = start_datetime.replace(" ", "T").replace("Z", "")
    formatted_end = end_datetime.replace(" ", "T").replace("Z", "")

    event = {
        "summary": summary,
        "description": description,
        "start": {
            "dateTime": formatted_start,
            "timeZone": timezone,
        },
        "end": {
            "dateTime": formatted_end,
            "timeZone": timezone,
        },
    }

    try:
        created_event = service.events().insert(
            calendarId="primary",
            body=event
        ).execute()
        return f"Success! Event created: {created_event.get('htmlLink')}"
    except Exception as e:
        return f"Failed to create event: {str(e)}"

def delete_calendar_event_for_date(
    target_date_str: str,
    summary: str = None,
):
    """
    Deletes calendar events for a specific date in IST.
    If summary is provided, deletes matching events for that date.
    If summary is not provided and multiple events exist, it asks for summary.
    """
    try:
        start_of_day = f"{target_date_str}T00:00:00+05:30"
        end_of_day = f"{target_date_str}T23:59:59+05:30"

        events_result = service.events().list(
            calendarId="primary",
            timeMin=start_of_day,
            timeMax=end_of_day,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = events_result.get("items", [])
        if not events:
            return f"No events found for {target_date_str}."

        if summary:
            filtered_events = [
                event for event in events
                if event.get("summary", "").strip().lower() == summary.strip().lower()
            ]
        else:
            filtered_events = events

        if not filtered_events:
            return f"No events found on {target_date_str} with summary '{summary}'."

        if summary is None and len(filtered_events) > 1:
            event_names = ", ".join(
                [event.get("summary", "No Title") for event in filtered_events]
            )
            return (
                f"Multiple events found on {target_date_str}: {event_names}. "
                "Please provide the event summary to delete the correct one."
            )

        deleted_count = 0
        for event in filtered_events:
            service.events().delete(
                calendarId="primary",
                eventId=event["id"],
            ).execute()
            deleted_count += 1

        if deleted_count == 1:
            return f"Deleted 1 event for {target_date_str}."
        return f"Deleted {deleted_count} events for {target_date_str}."

    except Exception as e:
        return f"Failed to delete event(s): {str(e)}"

def update_calendar_event_for_date(
    target_date_str: str,
    existing_summary: str,
    new_summary: str = None,
    new_description: str = None,
    new_start_datetime: str = None,
    new_end_datetime: str = None,
    timezone: str = "Asia/Kolkata",
):
    """
    Updates an existing event for a specific date in IST by matching its summary.
    At least one of the new_* fields should be provided.
    """
    try:
        start_of_day = f"{target_date_str}T00:00:00+05:30"
        end_of_day = f"{target_date_str}T23:59:59+05:30"

        events_result = service.events().list(
            calendarId="primary",
            timeMin=start_of_day,
            timeMax=end_of_day,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = events_result.get("items", [])
        matching_events = [
            event for event in events
            if event.get("summary", "").strip().lower() == existing_summary.strip().lower()
        ]

        if not matching_events:
            return (
                f"No event found on {target_date_str} with summary "
                f"'{existing_summary}'."
            )

        if len(matching_events) > 1:
            return (
                f"Multiple events found on {target_date_str} with summary "
                f"'{existing_summary}'. Please make the event name more specific."
            )

        if not any([new_summary, new_description, new_start_datetime, new_end_datetime]):
            return "No updates provided. Please supply at least one new field to update."

        event = matching_events[0]

        if new_summary:
            event["summary"] = new_summary
        if new_description:
            event["description"] = new_description
        if new_start_datetime:
            formatted_start = new_start_datetime.replace(" ", "T").replace("Z", "")
            event["start"] = {"dateTime": formatted_start, "timeZone": timezone}
        if new_end_datetime:
            formatted_end = new_end_datetime.replace(" ", "T").replace("Z", "")
            event["end"] = {"dateTime": formatted_end, "timeZone": timezone}

        updated_event = service.events().update(
            calendarId="primary",
            eventId=event["id"],
            body=event,
        ).execute()

        return f"Success! Event updated: {updated_event.get('htmlLink')}"

    except Exception as e:
        return f"Failed to update event: {str(e)}"

# --- Manual Test ---
if __name__ == "__main__":
    print("Current IST time:", get_current_datetime())
    
    # Note: Removed the 'Z' so it stays at 10:00 IST
    result = create_calendar_event(
        summary="Go to temple",
        description="Go to temple with family",
        start_datetime="2026-02-15T10:00:00", 
        end_datetime="2026-02-15T11:00:00",
    )
    print(result)

# --- Agent Configuration ---

model = LiteLlm(
    model="groq/qwen/qwen3-32b",  # use "groq/<groq-model-name>",
)
root_agent = Agent(
    model=model,
    name='root_agent',
    description="Manages and describes the user's calendar schedule in India Standard Time.",
    instruction="""
        Use 'get_current_datetime' to orient yourself to the user's current time.
        1. When asked about a schedule, always use 'get_schedule_for_date'. 
        2. Ensure the date is strictly in YYYY-MM-DD format.
        3. To add an event, use 'create_calendar_event'. 
        5. To delete an event for a date, use 'delete_calendar_event_for_date'.
        7. To update an event for a date, use 'update_calendar_event_for_date'.
        4. IMPORTANT: All times are in India Standard Time (IST). Do not append 'Z' to timestamps.
        6. Summarize the day's flow (e.g., 'You have a free morning before your 2 PM meeting').
    """,
    tools=[
        get_current_datetime,
        get_schedule_for_date,
        create_calendar_event,
        delete_calendar_event_for_date,
        update_calendar_event_for_date,
    ],
)

if __name__ == "__main__":
    # When run directly, start the agent. Importing this module won't auto-start it.
    root_agent.start()
