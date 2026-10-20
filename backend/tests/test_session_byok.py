from __future__ import annotations

import logging
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.security.session_manager import LLM_COOKIE, LLMSessionStore

from .conftest import CSRF, FakeLLMRegistry, make_settings, wait_for

USER_KEY = "sk-ant-user-secret-key-0123456789"


def save(
    client: TestClient,
    key: str = USER_KEY,
    provider: str = "anthropic",
    model: str = "claude-sonnet-5-5",
    test: bool = True,
):
    return client.post(
        "/api/session/llm-config",
        json={"provider": provider, "model": model, "api_key": key, "test": test},
        headers=CSRF,
    )


def test_valid_config_is_accepted_and_key_never_returned(
    client: TestClient, fake_llm: FakeLLMRegistry, caplog
):
    caplog.set_level(logging.DEBUG)
    resp = save(client)
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "session" and body["provider"] == "anthropic" and body["verified"] is True
    assert USER_KEY not in resp.text
    assert "api_key" not in body
    cookie_header = resp.headers.get("set-cookie", "")
    assert "atlas_llm=" in cookie_header and "HttpOnly" in cookie_header
    assert USER_KEY not in cookie_header
    assert fake_llm.keys_used() == {USER_KEY}  # the connection test used the user's key

    status = client.get("/api/session/llm-config")
    assert status.json()["source"] == "session"
    assert USER_KEY not in status.text
    assert USER_KEY not in caplog.text


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ({"provider": "cohere", "model": "x", "api_key": "k-12345678"}, "unsupported_provider"),
        ({"provider": "openai", "model": "bad model!", "api_key": "k-12345678"}, "invalid_model"),
    ],
)
def test_invalid_selection_rejected(client: TestClient, payload, code):
    resp = client.post("/api/session/llm-config", json=payload, headers=CSRF)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == code


def test_validation_error_does_not_echo_key(client: TestClient):
    resp = client.post(
        "/api/session/llm-config",
        json={"provider": "openai", "model": "gpt-5.5", "api_key": "short"},
        headers=CSRF,
    )
    assert resp.status_code == 422
    assert "short" not in resp.text


def test_failed_key_test_is_not_stored(client: TestClient):
    resp = save(client, key="bad-key-000000000")
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "llm_invalid_credentials"
    assert "bad-key" not in resp.text
    assert client.get("/api/session/llm-config").json()["source"] == "none"


def test_requires_csrf_header(client: TestClient):
    resp = client.post(
        "/api/session/llm-config", json={"provider": "anthropic", "model": "m", "api_key": USER_KEY}
    )
    assert resp.status_code == 403


def test_cross_origin_request_rejected(client: TestClient):
    resp = client.post(
        "/api/session/llm-config",
        json={"provider": "anthropic", "model": "m", "api_key": USER_KEY},
        headers={**CSRF, "Origin": "https://evil.example"},
    )
    assert resp.status_code == 403


def test_clear_configuration_removes_access(client: TestClient):
    save(client)
    resp = client.delete("/api/session/llm-config", headers=CSRF)
    assert resp.status_code == 204
    assert client.get("/api/session/llm-config").json()["source"] == "none"
    # Requests now have no model available (no default configured).
    r = client.post("/api/session/llm-config/test", headers=CSRF)
    assert r.status_code == 503


def test_users_cannot_access_each_others_configuration(client_factory, fake_llm: FakeLLMRegistry):
    alice, bob = client_factory(), client_factory()
    save(alice)
    assert bob.get("/api/session/llm-config").json()["source"] == "none"

    # Bob replays Alice's session cookie but keeps his own anonymous identity.
    stolen = alice.cookies.get(LLM_COOKIE)
    bob.cookies.set(LLM_COOKIE, stolen)
    assert bob.get("/api/session/llm-config").json()["source"] == "expired"
    resp = bob.post("/api/session/llm-config/test", headers=CSRF)
    assert resp.status_code == 409
    assert fake_llm.keys_used() == {USER_KEY}  # only Alice's own connection test


def test_forged_session_id_is_not_adopted(client: TestClient):
    client.cookies.set(LLM_COOKIE, "attacker-chosen-session-id")
    assert client.get("/api/session/llm-config").json()["source"] == "none"
    resp = save(client)
    issued = resp.cookies.get(LLM_COOKIE)
    assert issued and issued != "attacker-chosen-session-id"
    assert "attacker-chosen-session-id" not in issued


def test_session_id_rotates_on_each_save(client: TestClient):
    save(client)
    first = client.cookies.get(LLM_COOKIE)
    save(client)
    assert client.cookies.get(LLM_COOKIE) != first


def test_expired_configuration_cannot_be_used(client: TestClient, fake_llm: FakeLLMRegistry):
    save(client)
    store: LLMSessionStore = client.app.state.atlas.sessions  # type: ignore[attr-defined]
    store._clock = lambda: time.time() + store.ttl_seconds + 5  # type: ignore[method-assign]
    assert client.get("/api/session/llm-config").json()["source"] == "expired"
    resp = client.post("/api/session/llm-config/test", headers=CSRF)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "llm_session_expired"


async def test_store_expiry_and_owner_binding():
    now = [1000.0]
    store = LLMSessionStore(ttl_seconds=60, clock=lambda: now[0])
    from pydantic import SecretStr

    sid, _ = await store.create(
        owner_uid="u1", provider_id="openai", model="m", api_key=SecretStr("k"), verified=True
    )
    assert await store.get(sid, "u1") is not None
    assert await store.get(sid, "u2") is None
    now[0] += 61
    assert await store.get(sid, "u1") is None
    assert len(store) == 0


def test_test_endpoint_with_submitted_key_does_not_store(client: TestClient):
    resp = client.post(
        "/api/session/llm-config/test",
        json={
            "provider": "openrouter",
            "model": "nvidia/nemotron-3-super-120b-a12b:free",
            "api_key": "sk-or-temp-123456789",
        },
        headers=CSRF,
    )
    assert resp.status_code == 200 and resp.json()["source"] == "submitted"
    assert client.get("/api/session/llm-config").json()["source"] == "none"


def test_credential_endpoints_are_rate_limited(client: TestClient):
    codes = [save(client).status_code for _ in range(7)]
    assert 429 in codes


def test_failed_user_key_never_falls_back_to_default(
    tmp_path: Path, fake_llm: FakeLLMRegistry, monkeypatch: pytest.MonkeyPatch
):
    from app.api import research as research_api
    from app.security.url_validation import check_url
    from app.services import research_runner
    from app.services.document_fetcher import FetchResult

    async def fake_validate(url: str):
        return check_url(url)

    async def fake_fetch(url: str, client=None, **_):
        return FetchResult(
            requested_url=url, final_url=url, ok=True, title="Example OAuth", text="OAuth docs " * 20
        )

    monkeypatch.setattr(research_api, "validate_public_url", fake_validate)
    monkeypatch.setattr(research_runner, "fetch_document", fake_fetch)

    settings = make_settings(
        tmp_path,
        default_llm_provider="openrouter",
        default_llm_model="openai/gpt-5.5",
        openrouter_api_key="sk-or-operator-default-key",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        assert save(client, key="bad-user-key-12345", test=False).status_code == 200
        resp = client.post("/api/research", json={"query": "https://docs.example.com/oauth"}, headers=CSRF)
        assert resp.status_code == 202
        run_id = resp.json()["run_id"]
        wait_for(
            lambda: (
                client.get(f"/api/research/{run_id}").json()["status"] in ("failed", "partial", "completed")
            )
        )
        run = client.get(f"/api/research/{run_id}").json()
        assert run["status"] == "failed"
        assert run["error_code"] == "llm_invalid_credentials"
        assert run["llm"]["source"] == "session"
        chat = client.post("/api/guides/slack/chat", json={"question": "Which scopes?"}, headers=CSRF)
        assert chat.status_code == 400
        assert chat.json()["error"]["code"] == "llm_invalid_credentials"
    assert "sk-or-operator-default-key" not in fake_llm.keys_used()


def test_api_keys_never_written_to_database(tmp_path: Path, fake_llm: FakeLLMRegistry):
    settings = make_settings(tmp_path)
    app = create_app(settings)
    fake_llm.responder = lambda s, u: (
        '{"answer": "See C1.", "cited_claim_ids": ["C1"], "cited_source_ids": [], "grounding": "grounded"}'
    )
    with TestClient(app) as client:
        save(client)
        client.post("/api/guides/slack/chat", json={"question": "What scopes?"}, headers=CSRF)
        client.patch(
            "/api/guides/slack/checklist",
            json={"item_id": "check-create-app", "completed": True},
            headers=CSRF,
        )
    db_bytes = b"".join(p.read_bytes() for p in tmp_path.glob("atlas-test.db*"))
    assert db_bytes, "database file should exist"
    assert USER_KEY.encode() not in db_bytes
