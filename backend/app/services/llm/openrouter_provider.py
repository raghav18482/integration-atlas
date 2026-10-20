"""OpenRouter adapter: the `openai` SDK pointed at OpenRouter's OpenAI-compatible API."""

from __future__ import annotations

import openai
from openai import AsyncOpenAI

from app.services.llm.base import LLMEmptyResponse
from app.services.llm.openai_provider import map_openai_error

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterProvider:
    provider_id = "openrouter"

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        client: AsyncOpenAI | None = None,
        timeout: float = 120.0,
        app_url: str = "http://localhost:3000",
    ) -> None:
        self.model = model
        self._client = client or AsyncOpenAI(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL,
            timeout=timeout,
            max_retries=2,
            default_headers={"HTTP-Referer": app_url, "X-Title": "Integration Atlas"},
        )

    async def generate_text(self, system_prompt: str, user_prompt: str, *, max_tokens: int = 4096) -> str:
        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                # Reasoning models (e.g. Nemotron) can otherwise spend the whole budget on hidden
                # reasoning and return empty content. Ignored by models without reasoning.
                extra_body={"reasoning": {"effort": "low", "exclude": True}},
            )
        except openai.OpenAIError as exc:
            raise map_openai_error(self.provider_id, exc) from None
        choices = getattr(response, "choices", None) or []
        content = choices[0].message.content if choices and choices[0].message else None
        if not content or not content.strip():
            raise LLMEmptyResponse(self.provider_id)
        return content
