from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    dev_pilot_workspace: Path = Field(default=Path("./workspace"), alias="DEV_PILOT_WORKSPACE")

    # Token-saving defaults (lower than before).
    max_agent_steps: int = Field(default=5, alias="MAX_AGENT_STEPS", ge=1, le=20)
    max_file_chars: int = Field(default=4_000, alias="MAX_FILE_CHARS", ge=1000, le=100_000)
    history_keep_tool_results: int = Field(default=2, alias="HISTORY_KEEP_TOOL_RESULTS", ge=0, le=10)
    history_stub_chars: int = Field(default=300, alias="HISTORY_STUB_CHARS", ge=0, le=5000)

    # Failover order, comma-separated. Providers without an API key are skipped.
    provider_order: str = Field(default="openai,gemini,grok", alias="PROVIDER_ORDER")
    request_timeout_seconds: float = Field(default=60.0, alias="REQUEST_TIMEOUT_SECONDS", gt=0)

    # Model names change often: check each provider's docs and override in .env.
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")

    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash-lite", alias="GEMINI_MODEL")

    xai_api_key: str | None = Field(default=None, alias="XAI_API_KEY")
    xai_model: str = Field(default="grok-3-mini", alias="XAI_MODEL")

    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")

    @property
    def provider_names(self) -> list[str]:
        return [name.strip().lower() for name in self.provider_order.split(",") if name.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()