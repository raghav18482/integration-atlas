"""Shared fixtures. No test touches a real LLM, search API, or the network."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import Settings
from app.main import create_app
from app.services.llm import factory
from app.services.llm.base import LLMInvalidCredentials

CSRF = {"X-Atlas-CSRF": "1"}


@dataclass
class LLMCall:
    provider: str
    model: str
    api_key: str
    system: str
    user: str


@dataclass
class FakeLLMRegistry:
    """Replaces the real provider classes. Keys starting with 'bad' are rejected."""

    calls: list[LLMCall] = field(default_factory=list)
    responder: Callable[[str, str], str] = lambda system, user: "OK"

    def make(self, provider_id: str) -> type:
        registry = self

        class FakeProvider:
            def __init__(self, api_key: str, model: str, **_: object) -> None:
                self.provider_id = provider_id
                self.model = model
                self._key = api_key

            async def generate_text(
                self, system_prompt: str, user_prompt: str, *, max_tokens: int = 4096
            ) -> str:
                registry.calls.append(LLMCall(provider_id, self.model, self._key, system_prompt, user_prompt))
                if self._key.startswith("bad"):
                    raise LLMInvalidCredentials(provider_id)
                return registry.responder(system_prompt, user_prompt)

        return FakeProvider

    def keys_used(self) -> set[str]:
        return {c.api_key for c in self.calls}


@pytest.fixture
def fake_llm(monkeypatch: pytest.MonkeyPatch) -> FakeLLMRegistry:
    reg = FakeLLMRegistry()
    for pid in ("anthropic", "openai", "openrouter"):
        monkeypatch.setitem(factory._REGISTRY, pid, reg.make(pid))
    return reg


def make_settings(tmp_path: Path, **overrides: object) -> Settings:
    base: dict = {
        "environment": "test",
        "database_url": f"sqlite+aiosqlite:///{tmp_path}/atlas-test.db",
        "session_secret": SecretStr("test-secret-0123456789"),
        "tavily_api_key": None,
        "default_llm_provider": None,
        "default_llm_model": None,
        "anthropic_api_key": None,
        "openai_api_key": None,
        "openrouter_api_key": None,
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)  # type: ignore[call-arg]


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return make_settings(tmp_path)


@pytest.fixture
def client(settings: Settings, fake_llm: FakeLLMRegistry) -> Iterator[TestClient]:
    app = create_app(settings)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def client_factory(settings: Settings, fake_llm: FakeLLMRegistry) -> Iterator[Callable[[], TestClient]]:
    """Independent browsers (separate cookie jars) against one running app."""
    app = create_app(settings)
    with TestClient(app):  # runs lifespan once for the shared app
        yield lambda: TestClient(app)


def wait_for(predicate: Callable[[], bool], timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError("condition not met in time")
