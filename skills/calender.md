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
### `get_schedule_for_date`
### `create_calendar_event`
### `delete_calendar_event`
### `update_calendar_event`
### `get_free_slots_for_date`

## Tool Behavior Notes

- Schedule and free-slot queries expect `target_date_str` in `YYYY-MM-DD`.
- Event creation accepts `YYYY-MM-DD HH:MM:SS` or `YYYY-MM-DDTHH:MM:SS`.
- `format_datetime_input()` normalizes datetimes by replacing spaces with `T` and removing trailing `Z`.
- Calendar events are created and updated with timezone `Asia/Kolkata` by default.
- Schedule queries use `+05:30` day boundaries from `00:00:00` to `23:59:59`.
- `delete_calendar_event` and `update_calendar_event` operate by `event_id`, not by date.

## Important Note

- The current instruction text mentions `delete_calendar_event_for_date` and `update_calendar_event_for_date`, but the actual registered tool names in code are `delete_calendar_event` and `update_calendar_event`.
