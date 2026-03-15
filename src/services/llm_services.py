import os
from dataclasses import dataclass
from typing import Literal

from dotenv import load_dotenv
from google.adk.models import LiteLlm

Provider = Literal["groq", "google"]

DEFAULT_GROQ_MODEL = "groq/moonshotai/kimi-k2-instruct-0905"
DEFAULT_GOOGLE_MODEL = "gemini-3-flash-preview"


@dataclass(frozen=True)
class LLMConfig:
    provider: Provider = "groq"
    groq_model: str = DEFAULT_GROQ_MODEL
    google_model: str = DEFAULT_GOOGLE_MODEL


class LLMServices:
    """Centralized model factory for all agents."""

    def __init__(self, config: LLMConfig | None = None):
        load_dotenv()
        self.config = config or LLMConfig()
        self._ensure_env()

    @staticmethod
    def _ensure_env() -> None:
        # Keep values in process env so underlying SDKs can use them.
        google_api_key = os.getenv("GOOGLE_API_KEY")
        groq_api_key = os.getenv("GROQ_API_KEY")

        if google_api_key:
            os.environ["GOOGLE_API_KEY"] = google_api_key
        if groq_api_key:
            os.environ["GROQ_API_KEY"] = groq_api_key

    @staticmethod
    def _require_env(var_name: str) -> None:
        if not os.getenv(var_name):
            raise RuntimeError(f"Missing required environment variable: {var_name}")

    def get_groq_model(self, model_name: str | None = None) -> LiteLlm:
        self._require_env("GROQ_API_KEY")
        return LiteLlm(model=model_name or self.config.groq_model)

    def get_google_model(self, model_name: str | None = None) -> str:
        self._require_env("GOOGLE_API_KEY")
        return model_name or self.config.google_model

    def get_model(
        self,
        provider: Provider | None = None,
        *,
        model_name: str | None = None,
    ) -> LiteLlm | str:
        selected_provider = provider or self.config.provider
        if selected_provider == "groq":
            return self.get_groq_model(model_name=model_name)
        if selected_provider == "google":
            return self.get_google_model(model_name=model_name)
        raise ValueError(f"Unsupported provider: {selected_provider}")
