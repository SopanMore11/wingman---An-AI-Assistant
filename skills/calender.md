## Calendar Agent

- Agent file: `src/agents/calendar_agent/agent.py`
- Tools file: `src/agents/calendar_agent/tools.py`
- Auth helper: `src/google_authenticator.py`
- Imported in orchestrator: `src/agents/wingman_runtime.py`
- Agent variable name: `root_agent`
- Agent description: `Manages and describes the user's calendar schedule in India Standard Time.`
- Model: `groq/moonshotai/kimi-k2-instruct-0905` via `LiteLlm`
- Calendar service initialization happens at import time through `authenticate_google_calendar()`

## Agent Instruction

```text
Use 'get_current_datetime' to orient yourself to the user's current time.
1. When asked about a schedule, always use 'get_schedule_for_date'.
2. Ensure the date is strictly in YYYY-MM-DD format.
3. To add an event, use 'create_calendar_event'.
5. To delete an event for a date, use 'delete_calendar_event_for_date'.
7. To update an event for a date, use 'update_calendar_event_for_date'.
8. To find free time on a date, use 'get_free_slots_for_date'.
4. IMPORTANT: All times are in India Standard Time (IST). Do not append 'Z' to timestamps.
6. Summarize the day's flow (e.g., 'You have a free morning before your 2 PM meeting').
```

## Registered Tools

### `get_current_datetime`

- Path: `src/agents/calendar_agent/tools.py`
- Purpose: returns the current local datetime string used by the agent for orientation.

### `get_schedule_for_date`

- Path: `src/agents/calendar_agent/tools.py`
- Purpose: lists all Google Calendar events for one `YYYY-MM-DD` date in IST.

### `create_calendar_event`

- Path: `src/agents/calendar_agent/tools.py`
- Purpose: creates an event with `summary`, `description`, `start_datetime`, `end_datetime`, and optional `timezone`.

### `delete_calendar_event`

- Path: `src/agents/calendar_agent/tools.py`
- Purpose: deletes an event by `event_id`.

### `update_calendar_event`

- Path: `src/agents/calendar_agent/tools.py`
- Purpose: updates an existing event by `event_id` with optional new summary, description, start, or end.

### `get_free_slots_for_date`

- Path: `src/agents/calendar_agent/tools.py`
- Purpose: returns free slots within a configurable day window for one date.

## Tool Behavior Notes

- Schedule and free-slot queries expect `target_date_str` in `YYYY-MM-DD`.
- Event creation accepts `YYYY-MM-DD HH:MM:SS` or `YYYY-MM-DDTHH:MM:SS`.
- `format_datetime_input()` normalizes datetimes by replacing spaces with `T` and removing trailing `Z`.
- Calendar events are created and updated with timezone `Asia/Kolkata` by default.
- Schedule queries use `+05:30` day boundaries from `00:00:00` to `23:59:59`.
- `delete_calendar_event` and `update_calendar_event` operate by `event_id`, not by date.

## Important Note

- The current instruction text mentions `delete_calendar_event_for_date` and `update_calendar_event_for_date`, but the actual registered tool names in code are `delete_calendar_event` and `update_calendar_event`.
