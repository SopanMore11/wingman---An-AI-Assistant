# Wingman - An AI Calendar Assistant

Voice-enabled AI assistant that connects to Google Calendar and can:
- Read your schedule for a date
- Create calendar events
- Delete events for a date
- Update existing events

The project uses Google ADK + Groq model routing and Google Calendar API.

## Project Structure

- `main.py`: Voice loop + ADK runner entrypoint
- `src/agents/calenderAgent/agent.py`: Calendar agent and tools
- `src/google_authenticator.py`: Google OAuth + Calendar service setup
- `credentials.json`: Google OAuth client credentials (you provide this)
- `token.json`: Generated after first successful login

## Requirements

- Python `3.12+`
- Google Cloud project with Calendar API enabled
- OAuth client credentials JSON for desktop app
- Groq API key
- Google API key

## Installation

```powershell
uv sync
```

If you are not using `uv`, install dependencies from `pyproject.toml` with `pip`.

## Environment Variables

Create a `.env` file in project root:

```env
GOOGLE_API_KEY=your_google_api_key
GROQ_API_KEY=your_groq_api_key
```

## Google Calendar Authentication Setup

1. In Google Cloud Console, enable Google Calendar API.
2. Create OAuth credentials for a Desktop app.
3. Download the OAuth client file and save it as `credentials.json` in project root.
4. Run the app once; browser login will open and `token.json` will be created automatically.

## Run

```powershell
python main.py
```

Then speak commands into your microphone. Say `end` to stop.

## Calendar Tools Implemented

In `src/agents/calenderAgent/agent.py`, the agent exposes:

- `get_current_datetime()`
- `get_schedule_for_date(target_date_str)`
- `create_calendar_event(summary, description, start_datetime, end_datetime, timezone="Asia/Kolkata")`
- `delete_calendar_event_for_date(target_date_str, summary=None)`
- `update_calendar_event_for_date(target_date_str, existing_summary, new_summary=None, new_description=None, new_start_datetime=None, new_end_datetime=None, timezone="Asia/Kolkata")`

## Usage Notes

- Date format should be `YYYY-MM-DD`.
- Datetime format should be `YYYY-MM-DDTHH:MM:SS` (or `YYYY-MM-DD HH:MM:SS`).
- Assistant assumes India Standard Time (`Asia/Kolkata`).
- Do not append `Z` to timestamps for local IST event creation/update.

## Example Requests

- "What is my schedule for 2026-03-10?"
- "Create an event Team Sync on 2026-03-10 from 10:00 to 11:00."
- "Delete my event Dentist on 2026-03-10."
- "Update my event Team Sync on 2026-03-10 to start at 10:30 and end at 11:30."

## Troubleshooting

- Missing `credentials.json`: Google auth cannot start.
- Invalid/expired token: delete `token.json` and run again to re-authenticate.
- No microphone input: check system permissions and selected microphone device.
- Calendar not updating: confirm account login in OAuth browser flow matches expected Google account.
