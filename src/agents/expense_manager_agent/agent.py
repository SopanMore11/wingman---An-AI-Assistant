from datetime import datetime
from src.agents.base_agent import BaseAgent
from .tools import (
    add_daily_expense,
    monthly_category_expense,
    weekly_category_expense,
    get_expense_summary,
    search_expenses,
    top_spending_days,
    delete_expense,
    category_trend,
    edit_expense,
)


class ExpenseManagerAgent(BaseAgent):
    """Agent for managing and tracking daily expenses."""

    def __init__(self):
        super().__init__(
            name="expense_manager_agent",
            description="Tracks expenses and summarizes spending by category.",
            instruction=f"""
        You are an expense management assistant.
        Always use tools for actions and calculations; do not invent values.

        Tool usage rules:
        1. Use 'add_daily_expense' to save a new expense.
        2. Use 'monthly_category_expense' for monthly category totals.
        3. Use 'weekly_category_expense' for ISO-week category totals.
        4. Date input for adding expenses must be YYYY-MM-DD.
        5. If required fields are missing (date/category/description/amount), ask a concise follow-up.
        6. After tool calls, present a short readable summary.
        7. Current date and time is {datetime.now().isoformat()}. Use this for any time-sensitive decisions."
    """,
        )

    def _get_tools(self):
        """Return the list of tools available to this agent."""
        return [
            add_daily_expense,
            monthly_category_expense,
            weekly_category_expense,
            get_expense_summary,
            search_expenses,
            top_spending_days,
            delete_expense,
            category_trend,
            edit_expense,
        ]


# Export the agent instance
root_agent = ExpenseManagerAgent().agent

if __name__ == "__main__":
    # When run directly, start the agent. Importing this module won't auto-start it.
    root_agent.start()
