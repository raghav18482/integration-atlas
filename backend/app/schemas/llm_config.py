from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class LLMConfigRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = Field(max_length=32)
    model: str = Field(min_length=1, max_length=128)
    api_key: SecretStr
    test: bool = True

    @field_validator("api_key")
    @classmethod
    def _key_shape(cls, value: SecretStr) -> SecretStr:
        raw = value.get_secret_value().strip()
        if not 8 <= len(raw) <= 512 or any(ch.isspace() for ch in raw):
            raise ValueError("API key has an invalid format.")
        return SecretStr(raw)


class LLMConfigTestRequest(BaseModel):
    """Test the current configuration, or a submitted one without storing it."""

    model_config = ConfigDict(extra="forbid")

    provider: str | None = Field(default=None, max_length=32)
    model: str | None = Field(default=None, max_length=128)
    api_key: SecretStr | None = None


class DefaultLLMInfo(BaseModel):
    available: bool
    provider: str | None = None
    model: str | None = None


class LLMConfigStatus(BaseModel):
    source: Literal["session", "default", "none", "expired"]
    provider: str | None = None
    provider_label: str | None = None
    model: str | None = None
    verified: bool | None = None
    expires_at: datetime | None = None
    default: DefaultLLMInfo


class LLMTestResult(BaseModel):
    ok: bool
    provider: str
    model: str
    source: Literal["session", "default", "submitted"]
    latency_ms: int


class ProviderOption(BaseModel):
    id: str
    label: str
    sdk: str
    key_hint: str
    suggested_models: list[str]


class ProvidersResponse(BaseModel):
    providers: list[ProviderOption]
    default: DefaultLLMInfo
    search_configured: bool


class ModelsResponse(BaseModel):
    provider: str
    models: list[str]
    source: Literal["live", "suggested"]
