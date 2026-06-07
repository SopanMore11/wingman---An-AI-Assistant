"""Base agent class providing shared functionality for all agents."""

import logging
from abc import ABC, abstractmethod
from typing import Any

from google.adk.agents.llm_agent import Agent
from google.adk.models import LiteLlm

from src.config import Settings
from src.services.llm_services import LLMServices

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all Wingman agents."""

    def __init__(
        self,
        name: str,
        description: str,
        instruction: str,
        include_contents: str = 'default',  # Added parameter with default
        model: LiteLlm | str | None = None,
        settings: Settings | None = None,
    ):
        """
        Initialize the base agent.

        Args:
            name: Agent name identifier
            description: Agent description
            instruction: Agent system instruction
            include_contents: Controls history inheritance ('default' or 'none')
            model: LLM model instance (uses default if not provided)
            settings: Application settings (uses global if not provided)
        """
        self.name = name
        self.description = description
        self.instruction = instruction
        self.settings = settings or Settings.from_env()
        self.logger = logging.getLogger(f"wingman.{name}")

        # Initialize model if not provided
        if model is None:
            model = self._get_default_model()

        self._agent = Agent(
            name=name,
            model=model,
            description=description,
            instruction=instruction,
            include_contents=include_contents,  # Piped to the ADK agent
            tools=self._get_tools(),
        )

    def _get_default_model(self) -> LiteLlm | str:
        """Get the default LLM model from settings."""
        try:
            return LLMServices(config=self.settings.llm).get_model()
        except ValueError as e:
            self.logger.error(f"Failed to initialize default model: {e}")
            raise
        except RuntimeError as e:
            self.logger.error(f"Failed to initialize default model: {e}")
            raise

    @abstractmethod
    def _get_tools(self) -> list[Any]:
        """
        Get the list of tools available to this agent.

        Returns:
            List of tool definitions
        """
        pass

    @property
    def agent(self) -> Agent:
        """Get the underlying ADK Agent instance."""
        return self._agent

    def log_info(self, message: str) -> None:
        """Log info message."""
        self.logger.info(message)

    def log_error(self, message: str, exc: Exception | None = None) -> None:
        """Log error message."""
        if exc:
            self.logger.error(message, exc_info=exc)
        else:
            self.logger.error(message)

    def log_debug(self, message: str) -> None:
        """Log debug message."""
        self.logger.debug(message)