from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import anthropic
import httpx2
import openai
import pytest

from app.services.llm import factory
from app.services.llm.anthropic_provider import AnthropicProvider
from app.services.llm.base import (
    LLMEmptyResponse,
    LLMInsufficientCredits,
    LLMInvalidCredentials,
    LLMModelNotFound,
    LLMProvider,
    LLMRateLimited,
    LLMTimeout,
)
from app.services.llm.factory import (
    InvalidModelError,
    UnsupportedProviderError,
    create_provider,
    default_config,
    resolve_effective,
)
from app.services.llm.json_utils import StructuredOutputError, extract_json, generate_validated
from app.services.llm.openai_provider import OpenAIProvider
from app.services.llm.openrouter_provider import OPENROUTER_BASE_URL, OpenRouterProvider

from .conftest import make_settings


def _anthropic_client(create: AsyncMock) -> SimpleNamespace:
    return SimpleNamespace(messages=SimpleNamespace(create=create))


def _status_error(sdk, status: int, message: str):
    request = httpx2.Request("POST", "https://example.invalid/v1")
    cls = {401: sdk.AuthenticationError, 404: sdk.NotFoundError, 429: sdk.RateLimitError}.get(
        status, sdk.APIStatusError
    )
    return cls(message, response=httpx2.Response(status, request=request), body=None)


# ---------------------------------------------------------------- factory


def test_factory_selects_correct_sdk_adapter():
    assert isinstance(create_provider("anthropic", "claude-sonnet-5-5", "k-123456789"), AnthropicProvider)
    assert isinstance(create_provider("openai", "gpt-5.5", "k-123456789"), OpenAIProvider)
    assert isinstance(
        create_provider("openrouter", "anthropic/claude-sonnet-5.5", "k-123456789"), OpenRouterProvider
    )
    for p in ("anthropic", "openai", "openrouter"):
        assert isinstance(create_provider(p, "m", "k-123456789"), LLMProvider)


def test_openrouter_uses_openrouter_base_url_and_direct_openai_does_not():
    router = create_provider("openrouter", "nvidia/nemotron-3-super-120b-a12b", "k-123456789")
    assert str(router._client.base_url).rstrip("/") == OPENROUTER_BASE_URL  # type: ignore[attr-defined]
    direct = create_provider("openai", "gpt-5.5", "k-123456789")
    assert "openrouter" not in str(direct._client.base_url)  # type: ignore[attr-defined]
    assert "api.openai.com" in str(direct._client.base_url)  # type: ignore[attr-defined]


def test_anthropic_uses_anthropic_sdk_client():
    provider = create_provider("anthropic", "claude-sonnet-5-5", "k-123456789")
    assert isinstance(provider._client, anthropic.AsyncAnthropic)  # type: ignore[attr-defined]


def test_factory_rejects_unknown_provider_and_bad_model():
    with pytest.raises(UnsupportedProviderError):
        create_provider("cohere", "x", "k-123456789")
    with pytest.raises(InvalidModelError):
        create_provider("openai", "gpt 5; rm -rf", "k-123456789")
    with pytest.raises(ValueError):
        create_provider("openai", "gpt-5.5", "   ")


def test_resolve_effective_prefers_session_and_never_mixes(tmp_path):
    settings = make_settings(
        tmp_path,
        default_llm_provider="openrouter",
        default_llm_model="openai/gpt-5.5",
        openrouter_api_key="sk-or-default",
    )
    default = default_config(settings)
    assert default is not None and default.source == "default"
    session = factory.EffectiveLLMConfig(
        "anthropic", "claude-sonnet-5-5", "session", api_key=default.api_key.__class__("user-key")
    )
    chosen = resolve_effective(session, settings)
    assert chosen is session
    assert "user-key" not in repr(chosen)


def test_default_requires_key_for_selected_provider(tmp_path):
    settings = make_settings(
        tmp_path,
        default_llm_provider="anthropic",
        default_llm_model="claude-sonnet-5-5",
        openrouter_api_key="x",
    )
    assert default_config(settings) is None


# ---------------------------------------------------------------- adapters


async def test_anthropic_generate_text_calls_messages_create():
    create = AsyncMock(return_value=SimpleNamespace(content=[SimpleNamespace(type="text", text="hello")]))
    provider = AnthropicProvider("k", "claude-sonnet-5-5", client=_anthropic_client(create))  # type: ignore[arg-type]
    assert await provider.generate_text("sys", "user", max_tokens=100) == "hello"
    kwargs = create.call_args.kwargs
    assert kwargs["model"] == "claude-sonnet-5-5" and kwargs["system"] == "sys"
    assert kwargs["messages"] == [{"role": "user", "content": "user"}]


async def test_anthropic_empty_response():
    create = AsyncMock(return_value=SimpleNamespace(content=[]))
    provider = AnthropicProvider("k", "m", client=_anthropic_client(create))  # type: ignore[arg-type]
    with pytest.raises(LLMEmptyResponse):
        await provider.generate_text("s", "u")


async def test_openai_generate_text_calls_responses_create():
    create = AsyncMock(return_value=SimpleNamespace(output_text="answer"))
    client = SimpleNamespace(responses=SimpleNamespace(create=create))
    provider = OpenAIProvider("k", "gpt-5.5", client=client)  # type: ignore[arg-type]
    assert await provider.generate_text("sys", "user") == "answer"
    assert create.call_args.kwargs["instructions"] == "sys"
    assert create.call_args.kwargs["input"] == "user"


async def test_openrouter_generate_text_calls_chat_completions():
    msg = SimpleNamespace(message=SimpleNamespace(content="routed"))
    create = AsyncMock(return_value=SimpleNamespace(choices=[msg]))
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    provider = OpenRouterProvider("k", "nvidia/nemotron-3-super-120b-a12b", client=client)  # type: ignore[arg-type]
    assert await provider.generate_text("sys", "user") == "routed"
    messages = create.call_args.kwargs["messages"]
    assert messages[0] == {"role": "system", "content": "sys"}


@pytest.mark.parametrize(
    "payload",
    [
        SimpleNamespace(choices=[]),
        SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="  "))]),
    ],
)
async def test_openrouter_malformed_or_empty(payload):
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(return_value=payload)))
    )
    provider = OpenRouterProvider("k", "m", client=client)  # type: ignore[arg-type]
    with pytest.raises(LLMEmptyResponse):
        await provider.generate_text("s", "u")


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (401, LLMInvalidCredentials),
        (404, LLMModelNotFound),
        (429, LLMRateLimited),
        (402, LLMInsufficientCredits),
    ],
)
async def test_anthropic_errors_mapped_without_leaking_sdk_text(status, expected):
    err = _status_error(anthropic, status, "invalid x-api-key sk-ant-SECRET123456789")
    provider = AnthropicProvider("k", "m", client=_anthropic_client(AsyncMock(side_effect=err)))  # type: ignore[arg-type]
    with pytest.raises(expected) as info:
        await provider.generate_text("s", "u")
    assert "SECRET" not in info.value.message and "sk-ant" not in info.value.message
    assert info.value.__cause__ is None


async def test_openai_errors_mapped_without_leaking_sdk_text():
    err = _status_error(openai, 401, "Incorrect API key provided: sk-abc***SECRETxyz")
    client = SimpleNamespace(responses=SimpleNamespace(create=AsyncMock(side_effect=err)))
    provider = OpenAIProvider("k", "m", client=client)  # type: ignore[arg-type]
    with pytest.raises(LLMInvalidCredentials) as info:
        await provider.generate_text("s", "u")
    assert "SECRET" not in str(info.value)


async def test_openrouter_timeout_mapped():
    err = openai.APITimeoutError(
        request=httpx2.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(side_effect=err)))
    )
    provider = OpenRouterProvider("k", "m", client=client)  # type: ignore[arg-type]
    with pytest.raises(LLMTimeout):
        await provider.generate_text("s", "u")


# ---------------------------------------------------------------- structured output


def test_extract_json_handles_fences_and_prose():
    assert extract_json('Sure!\n```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('prefix {"b": [1, 2]} suffix') == {"b": [1, 2]}


async def test_generate_validated_retries_with_errors_then_fails():
    from pydantic import BaseModel

    class Out(BaseModel):
        n: int

    prompts: list[str] = []

    class Bad:
        provider_id, model = "fake", "m"

        async def generate_text(self, system_prompt, user_prompt, *, max_tokens=4096):
            prompts.append(user_prompt)
            return '{"n": "not a number"}'

    with pytest.raises(StructuredOutputError):
        await generate_validated(Bad(), "s", "base", Out, retries=2)
    assert len(prompts) == 3
    assert "rejected by the validator" in prompts[1]


async def test_anthropic_low_balance_maps_to_insufficient_credits():
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    err = anthropic.BadRequestError(
        "credit",
        response=httpx2.Response(400, request=request),
        body={
            "type": "error",
            "error": {
                "type": "invalid_request_error",
                "message": "Your credit balance is too low to access the Anthropic API.",
            },
        },
    )
    provider = AnthropicProvider("k", "m", client=_anthropic_client(AsyncMock(side_effect=err)))  # type: ignore[arg-type]
    with pytest.raises(LLMInsufficientCredits):
        await provider.generate_text("s", "u")
