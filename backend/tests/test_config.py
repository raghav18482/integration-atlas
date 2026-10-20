from __future__ import annotations

from pathlib import Path

import pytest

from app.config import Settings

EXAMPLE = Path(__file__).resolve().parents[1] / ".env.example"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch):
    for name in (
        "ALLOWED_ORIGINS",
        "DATABASE_URL",
        "DEFAULT_LLM_PROVIDER",
        "DEFAULT_LLM_MODEL",
        "OPENROUTER_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)


def test_env_example_loads(tmp_path: Path):
    s = Settings(_env_file=EXAMPLE)  # type: ignore[call-arg]
    assert s.allowed_origins == ["http://localhost:3000", "http://127.0.0.1:3000"]
    assert not s.default_llm_configured  # placeholders, no key


def test_comma_separated_origins_and_postgres_url(tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text(
        "ALLOWED_ORIGINS=https://atlas.example.com/, https://preview.example.com\n"
        "DATABASE_URL=postgres://u:p@db:5432/atlas\n"
        "DEFAULT_LLM_PROVIDER=openrouter\nDEFAULT_LLM_MODEL=anthropic/claude-sonnet-5.5\nOPENROUTER_API_KEY=sk-or-x\n"
    )
    s = Settings(_env_file=env)  # type: ignore[call-arg]
    assert s.allowed_origins == ["https://atlas.example.com", "https://preview.example.com"]
    assert s.database_url == "postgresql+asyncpg://u:p@db:5432/atlas"
    assert s.default_llm_configured
