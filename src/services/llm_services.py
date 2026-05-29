import os
from dataclasses import dataclass
from typing import Literal

from dotenv import load_dotenv
from google.adk.models import LiteLlm
from litai import LLM

Provider = Literal["groq", "google", "litai"]

DEFAULT_GROQ_MODEL = "groq/qwen/qwen3-32b"
DEFAULT_GOOGLE_MODEL = "gemini-3-flash-preview"
DEFAULT_LITAI_MODEL = "lightning-ai/gemma-4-31B-it"


@dataclass(frozen=True)
class LLMConfig:
    provider: Provider = "groq"
    groq_model: str = DEFAULT_GROQ_MODEL
    google_model: str = DEFAULT_GOOGLE_MODEL
    litai_model: str = DEFAULT_LITAI_MODEL


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
        lightning_api_key = os.getenv("LIGHTNING_API_KEY")

        if google_api_key:
            os.environ["GOOGLE_API_KEY"] = google_api_key
        if groq_api_key:
            os.environ["GROQ_API_KEY"] = groq_api_key
        if lightning_api_key:
            os.environ["LIGHTNING_API_KEY"] = lightning_api_key

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

    def get_litai_model(self, model_name: str | None = None) -> LLM:
        self._require_env("LIGHTNING_API_KEY")
        return LLM(
            model=model_name or self.config.litai_model,
            api_key=os.environ["LIGHTNING_API_KEY"],
        )

    def get_model(
        self,
        provider: Provider | None = None,
        *,
        model_name: str | None = None,
    ) -> LiteLlm | str | LLM:
        selected_provider = provider or self.config.provider
        if selected_provider == "groq":
            return self.get_groq_model(model_name=model_name)
        if selected_provider == "google":
            return self.get_google_model(model_name=model_name)
        if selected_provider == "litai":
            return self.get_litai_model(model_name=model_name)
        raise ValueError(f"Unsupported provider: {selected_provider}")
