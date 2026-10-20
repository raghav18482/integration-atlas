"""The app must restart cleanly against an existing database (seeds are re-upserted)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app

from .conftest import CSRF, make_settings


def test_restart_with_existing_database_keeps_progress(tmp_path: Path, fake_llm):
    settings = make_settings(tmp_path)
    with TestClient(create_app(settings)) as first:
        first.get("/api/guides/slack")
        first.patch(
            "/api/guides/slack/checklist",
            json={"item_id": "check-create-app", "completed": True},
            headers=CSRF,
        )
        cookies = dict(first.cookies)

    with TestClient(create_app(settings), cookies=cookies) as second:  # second startup, same DB file
        body = second.get("/api/guides/slack").json()
        assert body["checklist_progress"]["items"] == {"check-create-app": True}
        assert len(body["guide"]["claims"]) == 24
