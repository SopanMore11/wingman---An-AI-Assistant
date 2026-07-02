"""Centralized configuration settings for Wingman application."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast, get_args

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Define provider types
Provider = Literal["groq", "google", "litai", "litellm"]

DEFAULT_GROQ_MODEL = "groq/qwen2-7b-instruct"
DEFAULT_GOOGLE_MODEL = "gemini-2.0-flash"
DEFAULT_LITAI_MODEL = "google/gemini-2.5-flash-lite-preview-06-17"
DEFAULT_LITAI_API_BASE = "https://lightning.ai/api/v1"
DEFAULT_LITELLM_MODEL = DEFAULT_GROQ_MODEL

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
    groq_model: str = DEFAULT_GROQ_MODEL
    google_model: str = DEFAULT_GOOGLE_MODEL
    litai_model: str = DEFAULT_LITAI_MODEL
    litai_api_base: str = DEFAULT_LITAI_API_BASE
    litellm_model: str = DEFAULT_LITELLM_MODEL
    litellm_api_base: str | None = None
    groq_api_key_env: str = "GROQ_API_KEY"
    google_api_key_env: str = "GOOGLE_API_KEY"
    lightning_api_key_env: str = "LIGHTNING_API_KEY"
    litellm_api_key_env: str = "LITELLM_API_KEY"

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Create LLM configuration from environment variables."""
        provider = os.getenv("LLM_PROVIDER", "groq").strip().lower()
        if provider not in get_args(Provider):
            supported = ", ".join(get_args(Provider))
            raise ValueError(f"Unsupported LLM_PROVIDER '{provider}'. Use one of: {supported}")

        return cls(
            provider=cast(Provider, provider),
            groq_model=os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL),
            google_model=os.getenv("GOOGLE_MODEL", DEFAULT_GOOGLE_MODEL),
            litai_model=os.getenv("LITAI_MODEL", DEFAULT_LITAI_MODEL),
            litai_api_base=os.getenv("LITAI_API_BASE", DEFAULT_LITAI_API_BASE),
            litellm_model=os.getenv("LITELLM_MODEL", DEFAULT_LITELLM_MODEL),
            litellm_api_base=os.getenv("LITELLM_API_BASE") or None,
        )

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

    def get_lightning_api_key(self) -> str:
        """Get Lightning API key from environment."""
        key = os.getenv(self.lightning_api_key_env)
        if not key:
            raise ValueError(f"Missing environment variable: {self.lightning_api_key_env}")
        return key

    def get_litellm_api_key(self) -> str | None:
        """Get optional LiteLLM API key from environment."""
        return os.getenv(self.litellm_api_key_env)


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
            llm=LLMConfig.from_env(),
            calendar=CalendarConfig(),
            telegram=TelegramConfig(),
            debug=debug,
        )


# Global settings instance
settings = Settings.from_env()
