# Wingman

Wingman is a Telegram-native multi-agent assistant built with Google ADK. It takes ordinary chat messages, decides which specialist should handle them, uses tools to gather real data, and responds in a format that works cleanly inside Telegram.

This project is designed around one idea: an assistant should feel useful in day-to-day life, not just impressive in a demo. Wingman can manage calendar workflows, track expenses, search local job data, run live web searches, inspect browser pages, and switch LLM backends without changing the app architecture.

## What Makes It Interesting

- Multi-agent orchestration instead of one giant prompt.
- Tool-driven behavior for real work: calendar, expenses, jobs, internet search, browser inspection.
- Telegram-first output handling, including HTML-safe formatting.
- Flexible model routing through Groq, Google, Lightning AI, or generic LiteLLM-compatible providers.
- Local datasets and SQLite-backed workflows, so the assistant can do more than just "chat."

## What Wingman Can Do

- Calendar agent:
  Read schedules, create calendar-aware flows, and work with Google Calendar OAuth.
- Expense agent:
  Add, edit, delete, search, and summarize expenses stored in a local SQLite database.
- Job search agent:
  Query locally synced job data using location, keyword, company, recency, and date filters.
- Internet and browser agent:
  Search the web with Serper, inspect live browser pages over CDP, or open pages in a temporary Playwright browser and capture structured HTML.
- Orchestrator:
  Routes each user message to the right specialist, or coordinates multiple specialists in one conversation when needed.

## Architecture

The app runs as a Telegram bot, but the core is an ADK orchestrator that delegates work to focused sub-agents.

```text
Telegram message
    -> WingmanRuntime
    -> Orchestrator agent
    -> Specialist agent(s)
    -> Tool calls
    -> Telegram-safe final response
```

Key modules:

- [main.py](main.py)
- [src/agents/wingman_runtime.py](src/agents/wingman_runtime.py)
- [src/agents/calenderManager.py](src/agents/calenderManager.py)
- [src/agents/expenseManager.py](src/agents/expenseManager.py)
- [src/agents/jobSearcher.py](src/agents/jobSearcher.py)
- [src/agents/browserSearcher.py](src/agents/browserSearcher.py)
- [src/services/llm_services.py](src/services/llm_services.py)
- [src/integrations/telegram.py](src/integrations/telegram.py)

## Quick Start

### 1. Create a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -e .
```

If editable install does not work in your environment, install the listed dependencies from [pyproject.toml](pyproject.toml) manually.

### 2. Install Playwright browsers

```powershell
playwright install
```

### 3. Create `.env`

Use [.env.example](.env.example) as your template.

Minimum setup:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
LLM_PROVIDER=litai
LIGHTNING_API_KEY=your_lightning_api_key
LITAI_API_BASE=https://lightning.ai/api/v1
LITAI_MODEL=google/gemini-2.5-flash-lite-preview-06-17
SERPER_API_KEY=your_serper_api_key
```

### 4. Run the bot

```powershell
python .\main.py
```

## Model Switching

Wingman supports four provider modes today:

- `groq`
- `google`
- `litai`
- `litellm`

The simplest day-to-day switching pattern depends on what you want.

### Option A: Stay on Lightning AI and only swap models

Keep:

```env
LLM_PROVIDER=litai
LIGHTNING_API_KEY=your_lightning_api_key
LITAI_API_BASE=https://lightning.ai/api/v1
```

Then change only `LITAI_MODEL`.

Examples:

```env
LITAI_MODEL=google/gemini-2.5-flash-lite-preview-06-17
```

```env
LITAI_MODEL=lightning-ai/gemma-4-31B-it
```

```env
LITAI_MODEL=anthropic/claude-haiku-4-5-20251001
```

```env
LITAI_MODEL=openai/gpt-5-mini
```

This matches Lightning's OpenAI-compatible endpoint behavior and is the lowest-friction way to switch among models hosted there.

### Option B: Use LiteLLM as a universal provider switch

If you want to hop across providers using a single path, use:

```env
LLM_PROVIDER=litellm
LITELLM_MODEL=openai/gpt-4o
LITELLM_API_KEY=your_api_key
```

Examples:

```env
LITELLM_MODEL=openai/gpt-4o
```

```env
LITELLM_MODEL=google/gemini-2.5-flash
```

```env
LITELLM_MODEL=anthropic/claude-sonnet-4-0
```

Use `LITELLM_API_BASE` only when the endpoint is OpenAI-compatible and not the provider’s default public endpoint.

## Calendar Setup

Google Calendar features require OAuth credentials in addition to any model API key.

1. Create a Google Cloud project.
2. Enable the Google Calendar API.
3. Create OAuth Desktop credentials.
4. Place `credentials.json` in the repository root.
5. Run the app once and complete the browser auth flow. `token.json` will be created automatically.

## Example Prompts

- `Show my schedule for tomorrow`
- `Add an expense of 250 for lunch on 2026-07-02`
- `Edit my latest coffee expense and change the amount to 180`
- `Find Oracle jobs in Bengaluru from the last 7 days`
- `Search Google News for AI chip updates`
- `Inspect the current browser page and return the visible form fields`

## Project Structure

```text
src/
  agents/         Orchestrator and specialist agents
  tools/          Tool implementations for calendar, expenses, jobs, browser, internet
  services/       Model/provider wiring
  integrations/   Telegram integration
dataset/          Local database and source data
skills/           Agent instructions and tool usage guidance
tests/            Small project test suite
```

Notable tool modules:

- [src/tools/calender_tools.py](src/tools/calender_tools.py)
- [src/tools/expense_tools.py](src/tools/expense_tools.py)
- [src/tools/job_search_tools.py](src/tools/job_search_tools.py)
- [src/tools/browser_query_tools.py](src/tools/browser_query_tools.py)
- [src/tools/internet_tools.py](src/tools/internet_tools.py)

## Testing

Run what is available locally with:

```powershell
python -m pytest
```

If `pytest` is not installed in the active environment, install dependencies first with `pip install -e .`.

## Troubleshooting

- Missing `TELEGRAM_BOT_TOKEN`:
  The bot will not start.
- Missing model credentials:
  The orchestrator will fail during model initialization.
- Missing `SERPER_API_KEY`:
  Internet search tools will return structured error payloads.
- Missing `credentials.json`:
  Calendar features will not authenticate.
- Browser inspection not connecting:
  Start Chromium with `--remote-debugging-port=9222`, or use the local-browser capture path instead.

## Why This Repo Matters

Wingman is a useful reference if you care about any of these:

- building practical multi-agent systems with Google ADK
- shipping tool-using assistants in Telegram instead of a lab UI
- mixing local data, external APIs, and browser inspection in one assistant
- keeping model backends flexible without rewriting the application layer

It is a small project, but it is pointed at a real product shape: an assistant that can route, retrieve, act, and stay grounded in actual tools.
