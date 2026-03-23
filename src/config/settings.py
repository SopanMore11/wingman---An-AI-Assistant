"""Centralized configuration settings for Wingman application."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Define provider types
Provider = Literal["groq", "google"]

# Repository root path
REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class DatabaseConfig:
    """Database configuration."""

    db_path: str = "dataset/wingmandb.db"
    expense_csv_path: str = "dataset/my_expences.csv"
    env_var_name: str = "WINGMAN_DB_PATH"

    def resolve_db_path(self, db_file: str | None = None) -> Path:
        """Resolve the database file path."""
        if db_file:
            return Path(db_file)

        env_value = str(os.getenv(self.env_var_name, "")).strip()
        if env_value:
            return Path(env_value)

        return REPO_ROOT / self.db_path

    def resolve_expense_csv_path(self, csv_file: str | None = None) -> Path:
        """Resolve the expense CSV file path."""
        if csv_file:
            return Path(csv_file)
        return REPO_ROOT / self.expense_csv_path


@dataclass(frozen=True)
class LLMConfig:
    """LLM (Large Language Model) configuration."""

    provider: Provider = "groq"
    groq_model: str = "groq/moonshotai/kimi-k2-instruct-0905"
    google_model: str = "gemini-3-flash-preview"
    groq_api_key_env: str = "GROQ_API_KEY"
    google_api_key_env: str = "GOOGLE_API_KEY"

    def get_groq_api_key(self) -> str:
        """Get Groq API key from environment."""
        key = os.getenv(self.groq_api_key_env)
        if not key:
            raise ValueError(f"Missing environment variable: {self.groq_api_key_env}")
        return key

    def get_google_api_key(self) -> str:
        """Get Google API key from environment."""
        key = os.getenv(self.google_api_key_env)
        if not key:
            raise ValueError(f"Missing environment variable: {self.google_api_key_env}")
        return key


@dataclass(frozen=True)
class CalendarConfig:
    """Google Calendar configuration."""

    timezone: str = "Asia/Kolkata"
    day_start_hour: int = 0
    day_end_hour: int = 24
    credentials_file: str = "credentials.json"
    token_file: str = "token.json"

    def get_credentials_path(self) -> Path:
        """Get path to credentials file."""
        return REPO_ROOT / self.credentials_file

    def get_token_path(self) -> Path:
        """Get path to token file."""
        return REPO_ROOT / self.token_file


@dataclass(frozen=True)
class TelegramConfig:
    """Telegram bot configuration."""

    max_message_length: int = 4000
    token_env: str = "TELEGRAM_BOT_TOKEN"

    def get_token(self) -> str:
        """Get Telegram bot token from environment."""
        token = os.getenv(self.token_env)
        if not token:
            raise ValueError(f"Missing environment variable: {self.token_env}")
        return token


@dataclass(frozen=True)
class Settings:
    """Master settings configuration for Wingman application."""

    # Sub-configurations
    database: DatabaseConfig = DatabaseConfig()
    llm: LLMConfig = LLMConfig()
    calendar: CalendarConfig = CalendarConfig()
    telegram: TelegramConfig = TelegramConfig()

    # Application settings
    app_name: str = "wingman"
    debug: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        """Create Settings instance from environment variables."""
        debug = os.getenv("DEBUG", "").lower() == "true"

        return cls(
            database=DatabaseConfig(),
            llm=LLMConfig(),
            calendar=CalendarConfig(),
            telegram=TelegramConfig(),
            debug=debug,
        )


# Global settings instance
settings = Settings.from_env()
