"""Structured output on top of plain `generate_text`: extract JSON, validate, retry."""

from __future__ import annotations

import json
import re
from collections.abc import Callable

from pydantic import BaseModel, ValidationError

from app.services.llm.base import LLMProvider

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


class JSONExtractionError(ValueError):
    pass


class StructuredOutputError(Exception):
    """The model never produced a valid object within the retry budget."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors[:5]) or "Invalid structured output")


def extract_json(text: str) -> object:
    candidates = [m.group(1) for m in _FENCE.finditer(text)] + [text]
    decoder = json.JSONDecoder()
    for candidate in candidates:
        start = candidate.find("{")
        while start != -1:
            try:
                obj, _ = decoder.raw_decode(candidate[start:])
                return obj
            except json.JSONDecodeError:
                start = candidate.find("{", start + 1)
    raise JSONExtractionError("Response did not contain a JSON object.")


def summarize_validation_error(exc: ValidationError, limit: int = 12) -> list[str]:
    out = []
    for err in exc.errors()[:limit]:
        loc = ".".join(str(p) for p in err.get("loc", ()))
        out.append(f"{loc or '<root>'}: {err.get('msg', 'invalid')}")
    return out


async def generate_validated[T: BaseModel](
    llm: LLMProvider,
    system_prompt: str,
    user_prompt: str,
    model_cls: type[T],
    *,
    max_tokens: int = 4096,
    retries: int = 2,
    extra_check: Callable[[T], list[str]] | None = None,
    preprocess: Callable[[object], object] | None = None,
) -> T:
    prompt = user_prompt
    errors: list[str] = []
    for _attempt in range(retries + 1):
        text = await llm.generate_text(system_prompt, prompt, max_tokens=max_tokens)
        try:
            data = extract_json(text)
            obj = model_cls.model_validate(preprocess(data) if preprocess else data)
            errors = extra_check(obj) if extra_check else []
            if not errors:
                return obj
        except JSONExtractionError as exc:
            errors = [str(exc)]
        except ValidationError as exc:
            errors = summarize_validation_error(exc)
        prompt = (
            f"{user_prompt}\n\nYour previous response was rejected by the validator:\n- "
            + "\n- ".join(errors[:12])
            + "\nReturn a corrected, complete JSON object only."
        )
    raise StructuredOutputError(errors)
