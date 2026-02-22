from google_authenticator import authenticate_google_calendar
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

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

def get_free_slots_for_date(
    target_date_str: str,
    day_start: str = "09:00",
    day_end: str = "18:00",
    min_slot_minutes: int = 30,
):
    """
    Returns available free slots for a specific date in IST.
    - target_date_str: YYYY-MM-DD
    - day_start/day_end: HH:MM (24-hour)
    - min_slot_minutes: minimum free slot length to include
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

        day_start_dt = datetime.datetime.strptime(
            f"{target_date_str} {day_start}", "%Y-%m-%d %H:%M"
        )
        day_end_dt = datetime.datetime.strptime(
            f"{target_date_str} {day_end}", "%Y-%m-%d %H:%M"
        )

        if day_end_dt <= day_start_dt:
            return "Invalid day window. Ensure day_end is after day_start."

        busy_intervals = []
        for event in events:
            start_raw = event.get("start", {}).get("dateTime")
            end_raw = event.get("end", {}).get("dateTime")

            # All-day events block the full day window.
            if not start_raw or not end_raw:
                busy_intervals = [(day_start_dt, day_end_dt)]
                break

            start_dt = datetime.datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
            end_dt = datetime.datetime.fromisoformat(end_raw.replace("Z", "+00:00"))

            # Convert timezone-aware to naive local-style for consistent comparisons.
            if start_dt.tzinfo is not None:
                start_dt = start_dt.astimezone(datetime.timezone(datetime.timedelta(hours=5, minutes=30))).replace(tzinfo=None)
            if end_dt.tzinfo is not None:
                end_dt = end_dt.astimezone(datetime.timezone(datetime.timedelta(hours=5, minutes=30))).replace(tzinfo=None)

            # Clamp intervals to the requested day window.
            interval_start = max(start_dt, day_start_dt)
            interval_end = min(end_dt, day_end_dt)
            if interval_end > interval_start:
                busy_intervals.append((interval_start, interval_end))

        if not busy_intervals:
            return (
                f"Free slots for {target_date_str}:\n"
                f"[{day_start} - {day_end}]"
            )

        busy_intervals.sort(key=lambda x: x[0])
        merged = []
        for current_start, current_end in busy_intervals:
            if not merged or current_start > merged[-1][1]:
                merged.append([current_start, current_end])
            else:
                merged[-1][1] = max(merged[-1][1], current_end)

        free_slots = []
        cursor = day_start_dt
        min_delta = datetime.timedelta(minutes=min_slot_minutes)

        for busy_start, busy_end in merged:
            if busy_start - cursor >= min_delta:
                free_slots.append((cursor, busy_start))
            cursor = max(cursor, busy_end)

        if day_end_dt - cursor >= min_delta:
            free_slots.append((cursor, day_end_dt))

        if not free_slots:
            return f"No free slots of at least {min_slot_minutes} minutes on {target_date_str}."

        output = (
            f"Free slots for {target_date_str} "
            f"({day_start}-{day_end}, min {min_slot_minutes} min):\n"
        )
        for slot_start, slot_end in free_slots:
            output += f"[{slot_start.strftime('%H:%M')} - {slot_end.strftime('%H:%M')}]\n"

        return output.strip()

    except Exception as e:
        return f"Failed to fetch free slots: {str(e)}"
