"""Provider-agnostic LLM interface and safe error types.

Services depend only on `LLMProvider`; SDK imports live in the adapters.
Error messages are written by us, never copied from SDK exceptions (which can
echo request details such as a partially masked key).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

PROVIDER_LABELS = {"anthropic": "Anthropic", "openai": "OpenAI", "openrouter": "OpenRouter"}


@runtime_checkable
class LLMProvider(Protocol):
    provider_id: str
    model: str

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 4096,
    ) -> str: ...


class LLMError(Exception):
    code = "llm_error"
    http_status = 502
    template = "{label} request failed."

    def __init__(self, provider_id: str, message: str | None = None) -> None:
        self.provider_id = provider_id
        label = PROVIDER_LABELS.get(provider_id, provider_id)
        self.message = message or self.template.format(label=label)
        super().__init__(self.message)


class LLMInvalidCredentials(LLMError):
    code = "llm_invalid_credentials"
    http_status = 400
    template = "{label} rejected the API key. Check the key and try again."


class LLMPermissionDenied(LLMError):
    code = "llm_permission_denied"
    http_status = 400
    template = "{label} denied access for this key (permissions, billing, or model access)."


class LLMModelNotFound(LLMError):
    code = "llm_model_not_found"
    http_status = 400
    template = "{label} does not recognise this model ID, or this key cannot use it."


class LLMBadRequest(LLMError):
    code = "llm_bad_request"
    http_status = 400
    template = "{label} rejected the request for this model."


class LLMRateLimited(LLMError):
    code = "llm_rate_limited"
    http_status = 429
    template = "{label} rate limit reached. Wait a moment and retry."


class LLMInsufficientCredits(LLMError):
    code = "llm_insufficient_credits"
    http_status = 402
    template = "{label} reports insufficient credits for this key."


class LLMTimeout(LLMError):
    code = "llm_timeout"
    http_status = 504
    template = "{label} did not respond in time."


class LLMUnavailable(LLMError):
    code = "llm_unavailable"
    http_status = 502
    template = "{label} is unavailable or could not be reached."


class LLMEmptyResponse(LLMError):
    code = "llm_empty_response"
    http_status = 502
    template = "{label} returned an empty response."


class LLMNotConfigured(LLMError):
    code = "llm_not_configured"
    http_status = 503
    template = "No LLM is configured."


def map_status_error(provider_id: str, status: int | None) -> LLMError:
    if status == 401:
        return LLMInvalidCredentials(provider_id)
    if status == 402:
        return LLMInsufficientCredits(provider_id)
    if status == 403:
        return LLMPermissionDenied(provider_id)
    if status == 404:
        return LLMModelNotFound(provider_id)
    if status == 429:
        return LLMRateLimited(provider_id)
    if status in (400, 413, 422):
        return LLMBadRequest(provider_id)
    if status == 408:
        return LLMTimeout(provider_id)
    return LLMUnavailable(provider_id)
