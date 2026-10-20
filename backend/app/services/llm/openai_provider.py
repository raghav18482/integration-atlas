"""OpenAI adapter: uses the official `openai` SDK (Responses API) against api.openai.com."""

from __future__ import annotations

import openai
from openai import AsyncOpenAI

from app.services.llm.base import (
    LLMEmptyResponse,
    LLMError,
    LLMTimeout,
    LLMUnavailable,
    map_status_error,
)


def map_openai_error(provider_id: str, exc: openai.OpenAIError) -> LLMError:
    if isinstance(exc, openai.APITimeoutError):
        return LLMTimeout(provider_id)
    if isinstance(exc, openai.APIConnectionError):
        return LLMUnavailable(provider_id)
    if isinstance(exc, openai.APIStatusError):
        return map_status_error(provider_id, exc.status_code)
    return LLMUnavailable(provider_id)


class OpenAIProvider:
    provider_id = "openai"

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        client: AsyncOpenAI | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.model = model
        # No base_url override: direct OpenAI keys always go to OpenAI.
        self._client = client or AsyncOpenAI(api_key=api_key, timeout=timeout, max_retries=2)

    async def generate_text(self, system_prompt: str, user_prompt: str, *, max_tokens: int = 4096) -> str:
        try:
            response = await self._client.responses.create(
                model=self.model,
                instructions=system_prompt,
                input=user_prompt,
                # Reasoning models spend part of this budget on reasoning tokens.
                max_output_tokens=max(max_tokens * 2, 4096),
            )
        except openai.OpenAIError as exc:
            raise map_openai_error(self.provider_id, exc) from None
        text = getattr(response, "output_text", None) or ""
        if not text.strip():
            raise LLMEmptyResponse(self.provider_id)
        return text

    async def list_models(self) -> list[str]:
        try:
            page = await self._client.models.list()
        except openai.OpenAIError as exc:
            raise map_openai_error(self.provider_id, exc) from None
        return sorted(m.id for m in page.data)
