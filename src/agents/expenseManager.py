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


class ExpenseManagerAgent(BaseAgent):
    """Agent for managing and tracking daily expenses."""

    def __init__(self):
        super().__init__(
            name="expense_manager_agent",
            description="Tracks expenses and summarizes spending by category.",
            instruction=load_md_file("skills/expense.md"),
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
