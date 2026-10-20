"""Provider registry, factory, effective-config resolution, and model listing."""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

import httpx
from pydantic import SecretStr

from app.config import Settings, get_settings
from app.services.llm.anthropic_provider import AnthropicProvider
from app.services.llm.base import PROVIDER_LABELS, LLMError, LLMProvider, LLMUnavailable
from app.services.llm.openai_provider import OpenAIProvider
from app.services.llm.openrouter_provider import OPENROUTER_BASE_URL, OpenRouterProvider

MODEL_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/\-]{0,127}$")


class UnsupportedProviderError(ValueError):
    pass


class InvalidModelError(ValueError):
    pass


@dataclass(frozen=True)
class ProviderInfo:
    id: str
    label: str
    sdk: str
    key_hint: str
    # Model IDs confirmed to exist on 2026-10-20 (OpenRouter public model list /
    # Anthropic model names). Users can enter any ID; it is validated by a live test.
    suggested_models: tuple[str, ...]


PROVIDER_INFO: dict[str, ProviderInfo] = {
    "anthropic": ProviderInfo(
        id="anthropic",
        label="Anthropic",
        sdk="anthropic Python SDK",
        key_hint="sk-ant-…",
        suggested_models=("claude-sonnet-5-5", "claude-haiku-5-5", "claude-opus-5-5"),
    ),
    "openai": ProviderInfo(
        id="openai",
        label="OpenAI",
        sdk="openai Python SDK",
        key_hint="sk-…",
        suggested_models=("gpt-5.5", "gpt-4.1-mini"),
    ),
    "openrouter": ProviderInfo(
        id="openrouter",
        label="OpenRouter",
        sdk="openai Python SDK (OpenRouter base URL)",
        key_hint="sk-or-…",
        suggested_models=(
            "anthropic/claude-sonnet-5.5",
            "openai/gpt-5.5",
            "nvidia/nemotron-3-super-120b-a12b",
            "nvidia/nemotron-3-super-120b-a12b:free",
            # Free tier; confirmed fast enough for full research runs on 2026-10-20.
            "minimax/minimax-m3.1-flash:free",
        ),
    ),
}

_REGISTRY: dict[str, Callable[..., LLMProvider]] = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "openrouter": OpenRouterProvider,
}


def validate_provider_id(provider_id: str) -> str:
    if provider_id not in _REGISTRY:
        raise UnsupportedProviderError(
            f"Unsupported provider '{provider_id[:40]}'. Use one of: {', '.join(_REGISTRY)}."
        )
    return provider_id


def validate_model_id(model: str) -> str:
    if not MODEL_ID_PATTERN.fullmatch(model or ""):
        raise InvalidModelError("Model ID contains unsupported characters or is too long.")
    return model


def create_provider(provider_id: str, model: str, api_key: str) -> LLMProvider:
    validate_provider_id(provider_id)
    validate_model_id(model)
    if not api_key or not api_key.strip():
        raise ValueError("An API key is required.")
    kwargs: dict = {"api_key": api_key.strip(), "model": model}
    if provider_id == "openrouter":
        kwargs["app_url"] = get_settings().public_app_url
    return _REGISTRY[provider_id](**kwargs)


@dataclass(frozen=True)
class EffectiveLLMConfig:
    provider_id: str
    model: str
    source: Literal["session", "default"]
    api_key: SecretStr = field(repr=False)

    def build(self) -> LLMProvider:
        return create_provider(self.provider_id, self.model, self.api_key.get_secret_value())

    @property
    def label(self) -> str:
        return f"{PROVIDER_LABELS.get(self.provider_id, self.provider_id)} · {self.model}"


def default_config(settings: Settings) -> EffectiveLLMConfig | None:
    if not settings.default_llm_configured:
        return None
    assert settings.default_llm_provider and settings.default_llm_model
    key = settings.provider_key(settings.default_llm_provider)
    assert key is not None
    return EffectiveLLMConfig(
        provider_id=settings.default_llm_provider,
        model=settings.default_llm_model,
        source="default",
        api_key=key,
    )


def resolve_effective(
    session_config: EffectiveLLMConfig | None, settings: Settings
) -> EffectiveLLMConfig | None:
    """A session (BYOK) config always wins. If it later fails, callers surface the
    error; they never silently retry with the application's default key."""
    if session_config is not None:
        return session_config
    return default_config(settings)


# ---------------------------------------------------------------- model listing

_openrouter_cache: dict[str, tuple[float, list[str]]] = {}
_OPENROUTER_TTL = 3600.0


async def list_openrouter_models(client: httpx.AsyncClient | None = None) -> list[str]:
    cached = _openrouter_cache.get("models")
    if cached and time.monotonic() - cached[0] < _OPENROUTER_TTL:
        return cached[1]
    owns = client is None
    client = client or httpx.AsyncClient(timeout=15.0)
    try:
        resp = await client.get(f"{OPENROUTER_BASE_URL}/models")
        resp.raise_for_status()
        ids = sorted({m["id"] for m in resp.json().get("data", []) if isinstance(m, dict) and "id" in m})
    except (httpx.HTTPError, ValueError, KeyError):
        raise LLMUnavailable("openrouter", "Could not load the OpenRouter model list.") from None
    finally:
        if owns:
            await client.aclose()
    _openrouter_cache["models"] = (time.monotonic(), ids)
    return ids


async def list_models(provider_id: str, api_key: str | None) -> list[str]:
    validate_provider_id(provider_id)
    if provider_id == "openrouter":
        return await list_openrouter_models()
    if not api_key:
        raise LLMError(provider_id, "Provide an API key to list this provider's models.")
    provider = create_provider(provider_id, PROVIDER_INFO[provider_id].suggested_models[0], api_key)
    lister = getattr(provider, "list_models", None)
    if lister is None:
        return list(PROVIDER_INFO[provider_id].suggested_models)
    return await lister()
