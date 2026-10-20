"""Anthropic adapter: uses the official `anthropic` SDK directly."""

from __future__ import annotations

import anthropic
from anthropic import AsyncAnthropic

from app.services.llm.base import (
    LLMEmptyResponse,
    LLMError,
    LLMInsufficientCredits,
    LLMTimeout,
    LLMUnavailable,
    map_status_error,
)

# The SDK refuses non-streaming requests whose max_tokens implies >10 min.
_MAX_TOKENS_CAP = 16000


def _map_error(exc: anthropic.APIError) -> LLMError:
    if isinstance(exc, anthropic.APITimeoutError):
        return LLMTimeout("anthropic")
    if isinstance(exc, anthropic.APIConnectionError):
        return LLMUnavailable("anthropic")
    if isinstance(exc, anthropic.APIStatusError):
        # Anthropic reports an empty balance as a 400; surface it as a credits problem.
        error = (exc.body or {}).get("error", {}) if isinstance(exc.body, dict) else {}
        if exc.status_code == 400 and "credit balance" in str(error.get("message", "")).lower():
            return LLMInsufficientCredits("anthropic")
        return map_status_error("anthropic", exc.status_code)
    return LLMUnavailable("anthropic")


class AnthropicProvider:
    provider_id = "anthropic"

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        client: AsyncAnthropic | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.model = model
        self._client = client or AsyncAnthropic(api_key=api_key, timeout=timeout, max_retries=2)

    async def generate_text(self, system_prompt: str, user_prompt: str, *, max_tokens: int = 4096) -> str:
        try:
            response = await self._client.messages.create(
                model=self.model,
                max_tokens=min(max_tokens, _MAX_TOKENS_CAP),
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except anthropic.APIError as exc:
            raise _map_error(exc) from None
        text = "".join(
            getattr(block, "text", "")
            for block in (response.content or [])
            if getattr(block, "type", None) == "text"
        )
        if not text.strip():
            raise LLMEmptyResponse("anthropic")
        return text

    async def list_models(self) -> list[str]:
        try:
            page = await self._client.models.list(limit=100)
        except anthropic.APIError as exc:
            raise _map_error(exc) from None
        return [m.id for m in page.data]
