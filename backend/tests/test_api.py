from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.api.research import interpret_query

from .conftest import CSRF, FakeLLMRegistry


def test_health_and_guides_listing(client: TestClient):
    assert client.get("/api/health").json()["status"] == "ok"
    data = client.get("/api/guides").json()
    assert {i["slug"] for i in data["items"]} == {"slack", "github", "google"}
    assert all(i["origin"] == "seed" for i in data["items"])
    assert client.get("/api/guides", params={"q": "slack"}).json()["total"] == 1
    assert client.get("/api/guides", params={"origin": "live_research"}).json()["total"] == 0


def test_get_guide_and_missing_guide(client: TestClient):
    resp = client.get("/api/guides/github")
    assert resp.status_code == 200
    body = resp.json()
    assert body["guide"]["slug"] == "github"
    assert body["checklist_progress"]["total"] == len(body["guide"]["checklist_state"])
    assert all("excerpt" not in s for s in body["guide"]["sources"])
    missing = client.get("/api/guides/does-not-exist")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "not_found"
    assert client.get("/api/guides/Bad Slug!").status_code in (404, 422)


def test_checklist_persists_per_browser(client_factory):
    alice, bob = client_factory(), client_factory()
    alice.get("/api/guides/slack")  # mint identity
    resp = alice.patch(
        "/api/guides/slack/checklist", json={"item_id": "check-create-app", "completed": True}, headers=CSRF
    )
    assert resp.status_code == 200 and resp.json()["items"] == {"check-create-app": True}
    assert alice.get("/api/guides/slack").json()["checklist_progress"]["completed"] == 1
    assert bob.get("/api/guides/slack").json()["checklist_progress"]["completed"] == 0


def test_checklist_validation(client: TestClient):
    unknown = client.patch(
        "/api/guides/slack/checklist", json={"item_id": "check-nope", "completed": True}, headers=CSRF
    )
    assert unknown.status_code == 422 and unknown.json()["error"]["code"] == "unknown_checklist_item"
    bad = client.patch("/api/guides/slack/checklist", json={"item_id": "check-create-app"}, headers=CSRF)
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "validation_error"
    no_csrf = client.patch(
        "/api/guides/slack/checklist", json={"item_id": "check-create-app", "completed": True}
    )
    assert no_csrf.status_code == 403


def test_report_issue(client: TestClient):
    ok = client.post(
        "/api/guides/google/reports",
        json={"target_id": "publish", "message": "Step order looks wrong"},
        headers=CSRF,
    )
    assert ok.status_code == 201
    short = client.post("/api/guides/google/reports", json={"message": "no"}, headers=CSRF)
    assert short.status_code == 422


def test_research_requires_llm_and_validates_input(client: TestClient):
    assert client.post("/api/research", json={"query": "Notion"}, headers=CSRF).status_code == 503
    client.post(
        "/api/session/llm-config",
        json={"provider": "anthropic", "model": "claude-sonnet-5-5", "api_key": "sk-ant-good-12345678"},
        headers=CSRF,
    )
    # No search API configured: names need a docs URL.
    no_search = client.post("/api/research", json={"query": "Notion"}, headers=CSRF)
    assert no_search.status_code == 503 and no_search.json()["error"]["code"] == "search_not_configured"
    unsafe = client.post("/api/research", json={"query": "http://169.254.169.254/latest"}, headers=CSRF)
    assert unsafe.status_code == 400 and unsafe.json()["error"]["code"] == "unsafe_url"
    assert client.post("/api/research", json={"query": "x"}, headers=CSRF).status_code == 422
    assert (
        client.post(
            "/api/research", json={"query": "Notion", "integration_context": "galaxy"}, headers=CSRF
        ).status_code
        == 422
    )
    assert client.get("/api/research/00000000-0000-0000-0000-000000000000").status_code == 404


def test_interpret_query():
    assert interpret_query("Notion") == ("Notion", None)
    assert interpret_query("developers.notion.com/docs") == (
        "developers.notion.com/docs",
        "https://developers.notion.com/docs",
    )
    assert interpret_query("https://x.dev/a")[1] == "https://x.dev/a"
    assert interpret_query("Google Calendar")[1] is None


def test_chat_uses_the_requested_guide_and_strips_invented_citations(
    client: TestClient, fake_llm: FakeLLMRegistry
):
    client.post(
        "/api/session/llm-config",
        json={"provider": "openrouter", "model": "openai/gpt-5.5", "api_key": "sk-or-good-12345678"},
        headers=CSRF,
    )
    fake_llm.responder = lambda s, u: json.dumps(
        {
            "answer": "Marketplace review takes up to 10 weeks [C14].",
            "cited_claim_ids": ["C14", "C999"],
            "cited_source_ids": ["S3", "S42"],
            "grounding": "grounded",
        }
    )
    resp = client.post(
        "/api/guides/slack/chat",
        json={"question": "How long is review?", "history": [{"role": "user", "content": "hi"}]},
        headers=CSRF,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["cited_claim_ids"] == ["C14"] and body["cited_source_ids"] == ["S3"]
    assert body["llm"]["source"] == "session"
    prompt = fake_llm.calls[-1].user
    assert "Slack Marketplace" in prompt and "conversations.history" in prompt
    assert "GitHub Apps" not in prompt
    assert "QUESTION: How long is review?" in prompt


def test_chat_without_llm_is_explicit(client: TestClient):
    resp = client.post("/api/guides/slack/chat", json={"question": "What scopes?"}, headers=CSRF)
    assert resp.status_code == 503 and resp.json()["error"]["code"] == "llm_not_configured"


def test_refresh_of_seed_requires_llm(client: TestClient):
    assert client.post("/api/guides/slack/refresh", headers=CSRF).status_code == 503


def test_providers_endpoint_lists_three_independent_providers(client: TestClient):
    data = client.get("/api/llm/providers").json()
    ids = {p["id"]: p for p in data["providers"]}
    assert set(ids) == {"anthropic", "openai", "openrouter"}
    assert "OpenRouter base URL" in ids["openrouter"]["sdk"]
    assert data["default"]["available"] is False and data["search_configured"] is False
