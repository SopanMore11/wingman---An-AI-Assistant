# Wingman

Wingman is a Telegram-based AI assistant built with Google ADK. It routes user messages to specialized agents for:

- Google Calendar management
- Expense tracking
- Job search from a local SQLite database populated from the bundled datasets

The current application entrypoint is [`main.py`](/d:/My%20Programs/Python/Projects/wingman---An-AI-Assistant/main.py), which starts a Telegram bot and sends each chat message through a shared orchestrator runtime.

## Features

### Calendar agent

- Read a schedule for a given date
- Create, update, and delete calendar events
- Find free slots for a date
- Uses Google Calendar API with OAuth

### Expense manager agent

- Add daily expenses
- Search and edit saved expenses
- Delete expenses
- Summarize spending by date range, month, week, and category
- Show top spending days and category trends

### Job search agent

- Search jobs from a local SQLite dataset
- Filter by location, company, keyword, category, workplace type, and date
- List available filter metadata from the dataset
- Extract job details from a job URL when supported

## Architecture

- [`main.py`](/d:/My%20Programs/Python/Projects/wingman---An-AI-Assistant/main.py): starts the Telegram polling app
- [`src/agents/wingman_runtime.py`](/d:/My%20Programs/Python/Projects/wingman---An-AI-Assistant/src/agents/wingman_runtime.py): orchestrator runtime and session handling
- [`src/integrations/telegram.py`](/d:/My%20Programs/Python/Projects/wingman---An-AI-Assistant/src/integrations/telegram.py): Telegram bot integration
- [`src/agents/calendar_agent/agent.py`](/d:/My%20Programs/Python/Projects/wingman---An-AI-Assistant/src/agents/calendar_agent/agent.py): calendar agent
- [`src/agents/expense_manager_agent/agent.py`](/d:/My%20Programs/Python/Projects/wingman---An-AI-Assistant/src/agents/expense_manager_agent/agent.py): expense agent
- [`src/agents/job_search_agent/agent.py`](/d:/My%20Programs/Python/Projects/wingman---An-AI-Assistant/src/agents/job_search_agent/agent.py): job search agent
- [`src/google_authenticator.py`](/d:/My%20Programs/Python/Projects/wingman---An-AI-Assistant/src/google_authenticator.py): Google Calendar OAuth flow
- [`dataset/`](/d:/My%20Programs/Python/Projects/wingman---An-AI-Assistant/dataset): local SQLite database plus legacy source files used for bootstrapping

## Agent Skills Documentation

Each agent has detailed instructions and tool behavior documentation:

- [`skills/calender.md`](/d:/My%20Programs/Python/Projects/wingman---An-AI-Assistant/skills/calender.md): Calendar agent instructions, registered tools, and behavior notes
- [`skills/expense.md`](/d:/My%20Programs/Python/Projects/wingman---An-AI-Assistant/skills/expense.md): Expense manager agent instructions, registered tools, and behavior notes
- [`skills/job_search.md`](/d:/My%20Programs/Python/Projects/wingman---An-AI-Assistant/skills/job_search.md): Job search agent instructions, registered tools, and behavior notes

These documents provide comprehensive information about tool usage, date formats, validation rules, and response structures for each agent.

## Requirements

- Python `3.12+`
- A Telegram bot token
- A Groq API key
- A Google API key
- A Google Cloud project with Calendar API enabled
- OAuth desktop app credentials saved as `credentials.json`

## Installation

Using `uv`:

```powershell
uv sync
```

Then create a `.env` file in the project root:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_ALLOWED_USER_IDS=your_telegram_numeric_user_id
# Optional alternative to user IDs
# TELEGRAM_ALLOWED_CHAT_IDS=your_private_chat_id
GROQ_API_KEY=your_groq_api_key
GOOGLE_API_KEY=your_google_api_key
# Optional
WINGMAN_DB_PATH=dataset/wingmandb.db
```

## Google Calendar Setup

1. Open Google Cloud Console.
2. Enable the Google Calendar API for your project.
3. Create OAuth credentials for a Desktop app.
4. Download the client credentials file and save it as `credentials.json` in the project root.
5. Run the app once and complete the browser sign-in flow.
6. After a successful login, `token.json` will be created automatically.

## Run

```powershell
python main.py
```

The bot will start polling Telegram. Open your bot chat and send a message such as:

- `Show my schedule for 2026-03-16`
- `Add an expense of 250 for lunch on 2026-03-15`
- `Find Oracle jobs in Bengaluru`
- `/sendfile D:\My Programs\Python\Projects\wingman---An-AI-Assistant\README.md`

`/sendfile` only works for authorized Telegram users or chats listed in `TELEGRAM_ALLOWED_USER_IDS` or `TELEGRAM_ALLOWED_CHAT_IDS`.

## Data Files

- Primary app data is stored in [`dataset/wingmandb.db`](/d:/My%20Programs/Python/Projects/wingman---An-AI-Assistant/dataset/wingmandb.db)
- On first run, expense data is imported from [`dataset/my_expences.csv`](/d:/My%20Programs/Python/Projects/wingman---An-AI-Assistant/dataset/my_expences.csv)
- On first run, job data is imported from legacy JSON files in [`dataset/`](/d:/My%20Programs/Python/Projects/wingman---An-AI-Assistant/dataset), including `jpmorgan_jobs.json` and `oracle_jobs.json`

## Environment Variables

- `TELEGRAM_BOT_TOKEN`: required for the Telegram bot
- `TELEGRAM_ALLOWED_USER_IDS`: comma-separated Telegram user IDs allowed to use `/sendfile`
- `TELEGRAM_ALLOWED_CHAT_IDS`: optional comma-separated chat IDs allowed to use `/sendfile`
- `GROQ_API_KEY`: required for the Groq-backed models currently used by the agents
- `GOOGLE_API_KEY`: required by the configured Google ADK model integrations
- `WINGMAN_DB_PATH`: optional custom path for the SQLite database file

## Notes

- Calendar operations use India Standard Time (`Asia/Kolkata`) in the calendar tools.
- Job search now reads from the local SQLite database, which is bootstrapped from dataset files in this repository.
- The orchestrator tries to route each message to the single best sub-agent unless a request clearly combines multiple tasks.

## Troubleshooting

- Missing `TELEGRAM_BOT_TOKEN`: the app will fail during Telegram app startup.
- Missing `GROQ_API_KEY` or `GOOGLE_API_KEY`: model initialization will fail.
- Missing `credentials.json`: Google Calendar authentication cannot start.
- Invalid or expired Google token: delete `token.json` and run the app again.
- Empty or missing dataset files: job and expense features will return no results or file errors.
