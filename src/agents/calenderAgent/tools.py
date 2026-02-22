from google_authenticator import authenticate_google_calendar
import datetime
import os
from dotenv import load_dotenv

load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

service = authenticate_google_calendar()


def format_datetime_input(dt: str) -> str:
    """
    Normalizes datetime input for Calendar API usage.
    - Replaces spaces with 'T'
    - Removes trailing 'Z'
    """
    if dt is None:
        return dt
    return dt.replace(" ", "T").rstrip("Z")


def get_schedule_for_date(target_date_str: str) -> dict:
    """
    Fetches all events for a specific date in India Standard Time.
    :param target_date_str: A string in 'YYYY-MM-DD' format.
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
        event_items = []
        for event in events:
            start = event.get("start", {}).get("dateTime", event.get("start", {}).get("date"))
            end = event.get("end", {}).get("dateTime", event.get("end", {}).get("date"))
            event_items.append(
                {
                    "id": event.get("id"),
                    "summary": event.get("summary", ""),
                    "description": event.get("description", ""),
                    "start": start,
                    "end": end,
                    "htmlLink": event.get("htmlLink", ""),
                }
            )

        return {
            "status": "success",
            "date": target_date_str,
            "events": event_items,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_current_datetime() -> dict:
    """Returns the current date and time in IST-compatible format."""
    now = datetime.datetime.now()
    return {"status": "success", "current_datetime": now.strftime("%Y-%m-%d %H:%M:%S")}


def create_calendar_event(
    summary: str,
    description: str,
    start_datetime: str,
    end_datetime: str,
    timezone: str = "Asia/Kolkata",
) -> dict:
    """
    Creates a calendar event.
    Accepts formats: 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DDTHH:MM:SS'
    """
    try:
        formatted_start = format_datetime_input(start_datetime)
        formatted_end = format_datetime_input(end_datetime)

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

        created_event = service.events().insert(
            calendarId="primary",
            body=event,
        ).execute()

        return {
            "status": "success",
            "event": {
                "id": created_event.get("id"),
                "summary": created_event.get("summary", ""),
                "start": created_event.get("start", {}).get("dateTime", created_event.get("start", {}).get("date")),
                "end": created_event.get("end", {}).get("dateTime", created_event.get("end", {}).get("date")),
                "htmlLink": created_event.get("htmlLink", ""),
            },
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def delete_calendar_event(event_id: str) -> dict:
    """
    Deletes a calendar event by event_id.
    """
    try:
        service.events().delete(
            calendarId="primary",
            eventId=event_id,
        ).execute()
        return {"status": "success", "deleted_event_id": event_id}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def update_calendar_event(
    event_id: str,
    new_summary: str = None,
    new_description: str = None,
    new_start_datetime: str = None,
    new_end_datetime: str = None,
    timezone: str = "Asia/Kolkata",
) -> dict:
    """
    Updates an existing event by event_id.
    Updates only provided fields.
    """
    try:
        if not any([new_summary, new_description, new_start_datetime, new_end_datetime]):
            return {"status": "error", "message": "No update fields provided."}

        event = service.events().get(
            calendarId="primary",
            eventId=event_id,
        ).execute()

        if new_summary is not None:
            event["summary"] = new_summary
        if new_description is not None:
            event["description"] = new_description
        if new_start_datetime is not None:
            formatted_start = format_datetime_input(new_start_datetime)
            event["start"] = {"dateTime": formatted_start, "timeZone": timezone}
        if new_end_datetime is not None:
            formatted_end = format_datetime_input(new_end_datetime)
            event["end"] = {"dateTime": formatted_end, "timeZone": timezone}

        updated_event = service.events().update(
            calendarId="primary",
            eventId=event_id,
            body=event,
        ).execute()

        return {
            "status": "success",
            "event": {
                "id": updated_event.get("id"),
                "summary": updated_event.get("summary", ""),
                "start": updated_event.get("start", {}).get("dateTime", updated_event.get("start", {}).get("date")),
                "end": updated_event.get("end", {}).get("dateTime", updated_event.get("end", {}).get("date")),
                "htmlLink": updated_event.get("htmlLink", ""),
            },
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_free_slots_for_date(
    target_date_str: str,
    day_start: str = "09:00",
    day_end: str = "18:00",
    min_slot_minutes: int = 30,
) -> dict:
    """
    Returns available free slots for a specific date in IST.
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
            return {"status": "error", "message": "Invalid day window. Ensure day_end is after day_start."}

        busy_intervals = []
        for event in events:
            start_raw = event.get("start", {}).get("dateTime")
            end_raw = event.get("end", {}).get("dateTime")

            if not start_raw or not end_raw:
                busy_intervals = [(day_start_dt, day_end_dt)]
                break

            start_dt = datetime.datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
            end_dt = datetime.datetime.fromisoformat(end_raw.replace("Z", "+00:00"))

            if start_dt.tzinfo is not None:
                start_dt = start_dt.astimezone(
                    datetime.timezone(datetime.timedelta(hours=5, minutes=30))
                ).replace(tzinfo=None)
            if end_dt.tzinfo is not None:
                end_dt = end_dt.astimezone(
                    datetime.timezone(datetime.timedelta(hours=5, minutes=30))
                ).replace(tzinfo=None)

            interval_start = max(start_dt, day_start_dt)
            interval_end = min(end_dt, day_end_dt)
            if interval_end > interval_start:
                busy_intervals.append((interval_start, interval_end))

        if not busy_intervals:
            return {
                "status": "success",
                "date": target_date_str,
                "day_start": day_start,
                "day_end": day_end,
                "min_slot_minutes": min_slot_minutes,
                "free_slots": [{"start": day_start, "end": day_end}],
            }

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
            return {
                "status": "success",
                "date": target_date_str,
                "day_start": day_start,
                "day_end": day_end,
                "min_slot_minutes": min_slot_minutes,
                "free_slots": [],
            }

        slots = [
            {"start": slot_start.strftime("%H:%M"), "end": slot_end.strftime("%H:%M")}
            for slot_start, slot_end in free_slots
        ]
        return {
            "status": "success",
            "date": target_date_str,
            "day_start": day_start,
            "day_end": day_end,
            "min_slot_minutes": min_slot_minutes,
            "free_slots": slots,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
