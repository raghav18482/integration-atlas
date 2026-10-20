"""Application settings, read from environment variables (and backend/.env locally).

Every provider credential is optional: the app must start and serve seed guides
with no keys configured at all.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

ProviderId = Literal["anthropic", "openai", "openrouter"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["development", "production", "test"] = "development"

    # Application-default LLM (only the selected provider needs a key).
    default_llm_provider: ProviderId | None = None
    default_llm_model: str | None = None
    anthropic_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    openrouter_api_key: SecretStr | None = None

    # Search
    tavily_api_key: SecretStr | None = None

    # Storage. Production runs `alembic upgrade head` and sets AUTO_CREATE_TABLES=false.
    database_url: str = "sqlite+aiosqlite:///./atlas.db"
    auto_create_tables: bool = True

    # Sessions & security
    session_secret: SecretStr = SecretStr("dev-only-insecure-secret-change-me")
    cookie_secure: bool = False
    # NoDecode: accept "a,b" from env files instead of requiring JSON.
    allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )
    byok_ttl_minutes: int = 60
    public_app_url: str = "http://localhost:3000"

    # Rate limits (requests per window)
    rate_limit_llm_config_per_minute: int = 5
    rate_limit_research_default_per_hour: int = 6
    rate_limit_research_byok_per_hour: int = 20
    rate_limit_chat_per_hour: int = 30

    # Research bounds
    research_max_sources: int = 12
    research_timeout_seconds: int = 300

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                return value  # JSON list; let pydantic parse it
            return [v.strip().rstrip("/") for v in stripped.split(",") if v.strip()]
        return value

    @field_validator("database_url")
    @classmethod
    def _async_driver(cls, value: str) -> str:
        # Render/Heroku-style URLs use postgres:// or postgresql://; we need asyncpg.
        if value.startswith("postgres://"):
            value = "postgresql://" + value[len("postgres://") :]
        if value.startswith("postgresql://"):
            value = "postgresql+asyncpg://" + value[len("postgresql://") :]
        return value

    def provider_key(self, provider: ProviderId) -> SecretStr | None:
        return {
            "anthropic": self.anthropic_api_key,
            "openai": self.openai_api_key,
            "openrouter": self.openrouter_api_key,
        }[provider]

    @property
    def default_llm_configured(self) -> bool:
        if not self.default_llm_provider or not self.default_llm_model:
            return False
        key = self.provider_key(self.default_llm_provider)
        return bool(key and key.get_secret_value())

    @property
    def search_configured(self) -> bool:
        return bool(self.tavily_api_key and self.tavily_api_key.get_secret_value())


@lru_cache
def get_settings() -> Settings:
    return Settings()
