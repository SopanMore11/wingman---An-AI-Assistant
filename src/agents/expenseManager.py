from datetime import datetime

from src.agents.base_agent import BaseAgent
from src.utils import load_md_file
from src.tools.expense_tools import (
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


def _build_expense_instruction() -> str:
    today = datetime.now().date()
    first_day_of_month = today.replace(day=1)
    return (
        load_md_file("skills/expense.md").strip()
        + "\n\n"
        + "Current runtime date context:\n"
        + f"- Today is {today.isoformat()}.\n"
        + f"- The first day of this month is {first_day_of_month.isoformat()}.\n"
        + "- Resolve relative phrases like 'today', 'yesterday', 'this week', and 'this month' using these dates.\n"
        + "- For 'this month', use the first day of this month through today unless the user asks for the full calendar month explicitly.\n"
    )


class ExpenseManagerAgent(BaseAgent):
    """Agent for managing and tracking daily expenses."""

    def __init__(self):
        super().__init__(
            name="expense_manager_agent",
            description="Tracks expenses and summarizes spending by category.",
            instruction=_build_expense_instruction(),
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


def build_expense_agent():
    return ExpenseManagerAgent().agent
