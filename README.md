# Integration Atlas

**Know what it takes to launch an integration before you build it.**

Developers building AI agents need their users to connect third-party apps. That usually means registering an OAuth app with the provider, choosing scopes, and sometimes passing verification or marketplace review. Integration Atlas researches those requirements and produces a shareable, evidence-backed setup guide. The guide separates hands-on effort from external waiting, keeps each approval gate distinct, and labels every claim with how it was supported.

It is not a chatbot. It is a research workspace that turns provider documentation into structured guides, with contextual Q&A grounded in each guide's evidence.

---

## 1. Product overview

| You want to know… | Where the guide answers it |
|---|---|
| How hard is this, and where do I start? | Overview, recommended path (managed OAuth vs. your own OAuth app vs. API key), ordered setup steps |
| How long will it take? | **Active effort** (hands-on hours, estimated) vs. **external waiting** (only shown when the provider documents it) |
| What could block launch? | Approval & launch gates, kept separate: registration, user consent, admin consent, provider verification, marketplace listing, production access. Also blockers and unknowns. |
| What can an agent do vs. me? | "Agent can do / agent drafts, you approve / you must do" |
| Can I trust it? | Every claim links to a source, and its status (Tested, Cross-checked, Documented, Inferred, Estimated, Unknown) is assigned by code, not by the model |

Three **seed guides** show deliberately different setup challenges:

| Seed | Why it is interesting |
|---|---|
| **Slack** | Self-serve distribution, but since May 2025 unlisted commercial apps get 1 request/minute on `conversations.history`. Marketplace listing needs 10+ active workspaces and takes up to 10 business days + 10 weeks. |
| **GitHub** | GitHub App vs. OAuth App choice and fine-grained permissions. No review for direct installs. Marketplace thresholds apply to *paid* listings only. |
| **Google (Gmail/Calendar)** | Sensitive vs. restricted scopes, testing-mode 100-user cap and 7-day grant expiry, and an annual third-party security assessment (CASA) for Gmail. |

**Live research** handles any other app: enter a name or a docs URL, watch the real pipeline stages, and get a saved guide at a stable URL.

## 2. Main features

- **Discovery:** app name or docs URL, intended use case, and integration context (personal / internal / multi-user SaaS).
- **Research workspace:** real stage events, sources discovered/retrieved/failed, and partial results with retry.
- **Guide workspace:**
  - Three-column layout.
  - Summary strip (effort, waiting, approval, auth model).
  - Step cards with owner, effort, dependencies, evidence chips, and verification status.
  - Scopes, approval gates, testing plan, blockers and unknowns, agent-vs-developer, and context variations.
  - "How it was checked" report.
- **Evidence panel:** every claim with its verbatim quote, test detail, and source links; every source with its retrieval status and the claims it supports.
- **Contextual Q&A:** grounded in the saved guide and its evidence; reports when evidence is insufficient.
- **Checklist:** progress persisted per browser (shared links show the guide, not your ticks).
- **Saved guides:** search, origin filter (seed / live), generated and last-checked dates, evidence status.
- **LLM settings:** use the app default, or bring your own Anthropic / OpenAI / OpenRouter key for this session only.
- **Report an issue** on any step or claim.

## 3. Architecture

```
Browser ──► Next.js (frontend/)  ── rewrites /api/* ──►  FastAPI (backend/)
            App Router, Tailwind,                           │
            shadcn/ui                                       ├─ Research workflow (bounded, explicit)
                                                            │    search (Tavily) → fetch (SSRF-safe httpx)
                                                            │    → per-topic claim extraction (LLM)
                                                            │    → deterministic quote checks
                                                            │    → OAuth metadata probe
                                                            │    → guide draft (LLM) → validation rules
                                                            ├─ LLMProvider interface
                                                            │    Anthropic SDK · OpenAI SDK · OpenRouter (OpenAI SDK + base_url)
                                                            ├─ In-memory BYOK session store (signed cookies)
                                                            └─ SQLAlchemy (SQLite locally / Postgres in prod)
```

- The browser only talks to the Next.js origin, so the backend's HttpOnly cookies stay first-party and no CORS is needed.
- Research runs as an in-process `asyncio` task. Each stage writes events to the `research_runs` row, and the UI polls every 1.5 s.
- Pydantic's `IntegrationGuide` schema enforces referential integrity: claims→sources and steps/scopes/approvals→claims must exist, `tested` requires a test record, and `documented` requires a retrieved page.

Key backend files:

| Concern | File |
|---|---|
| Guide schema and enums | `backend/app/schemas/guide.py` |
| LLM interface and adapters | `backend/app/services/llm/{base,anthropic_provider,openai_provider,openrouter_provider,factory}.py` |
| Structured output (JSON → Pydantic, bounded retries) | `backend/app/services/llm/json_utils.py` |
| Research pipeline | `backend/app/services/research_workflow.py` |
| Quote verification and claim status | `backend/app/services/evidence.py` |
| Evidence rules (coercions, effort) | `backend/app/services/guide_generator.py` |
| SSRF protection / fetching | `backend/app/security/url_validation.py`, `backend/app/services/document_fetcher.py` |
| BYOK sessions, CSRF, rate limits | `backend/app/security/` |
| Seed guides | `backend/app/seed/guides/*.json` |

## 4. Technology choices

- **No LangChain, LangGraph, or agent framework.** The workflow is fixed and bounded, and the hard part is evidence handling, which is plain Python we control and test.
- **Direct SDKs behind one small `LLMProvider` protocol.** Anthropic keys use the `anthropic` SDK. OpenAI keys use the `openai` SDK (Responses API). OpenRouter keys use the `openai` SDK with `base_url="https://openrouter.ai/api/v1"`. Provider endpoints are server-side constants; the frontend can't supply a base URL.
- **Tavily** for search (domain filtering, simple REST). It sits behind a `SearchClient` protocol.
- **httpx + BeautifulSoup** for retrieval and extraction; **rapidfuzz** only for tightly constrained near-matching of quotes.
- **SQLite** locally (zero setup), **Postgres** in production; **Alembic** migrations.
- **Polling, not SSE.** It is simpler and robust behind proxies, and the events are real either way.

## 5. Local setup

Prerequisites: Node 20+ (tested with 24), [uv](https://docs.astral.sh/uv/) (installs Python 3.12 for you).

Set up the backend:

```bash
cd backend
cp .env.example .env        # add keys as needed (see §6); none are required to browse seed guides
uv sync
```

Set up the frontend:

```bash
cd frontend
cp .env.example .env.local  # BACKEND_URL=http://127.0.0.1:8000
npm install
```

## 6. Environment variables

**Backend** (`backend/.env`, see `backend/.env.example`):

| Variable | Purpose |
|---|---|
| `DEFAULT_LLM_PROVIDER` | `anthropic`, `openai`, or `openrouter`. The app default used when a visitor has no own key. |
| `DEFAULT_LLM_MODEL` | A real model ID for that provider (e.g. `claude-sonnet-5-5`, `gpt-5.5`, `anthropic/claude-sonnet-5.5`) |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `OPENROUTER_API_KEY` | Only the default provider needs one; missing keys never block startup |
| `TAVILY_API_KEY` | Web search for live research by app name |
| `DATABASE_URL` | Default `sqlite+aiosqlite:///./atlas.db`; `postgres://…` URLs are converted to asyncpg automatically |
| `AUTO_CREATE_TABLES` | `true` locally; `false` in production (use Alembic) |
| `SESSION_SECRET` | Signs the anonymous-browser and BYOK cookies. **Set a long random value in production.** |
| `COOKIE_SECURE` | `true` in production (HTTPS-only cookies) |
| `ALLOWED_ORIGINS` | Comma-separated frontend origins allowed to make state-changing requests |
| `PUBLIC_APP_URL` | Sent to OpenRouter as `HTTP-Referer` |
| `BYOK_TTL_MINUTES` | Lifetime of a session key in memory (default 60) |
| `RATE_LIMIT_*` | Per-browser/IP limits for key tests, research, and chat |

**Frontend** (`frontend/.env.local`): `BACKEND_URL`, used server-side only by the `/api` rewrite.

## 7. Frontend startup

```bash
cd frontend && npm run dev     # http://localhost:3000
```

## 8. Backend startup

```bash
cd backend && uv run uvicorn app.main:app --reload --port 8000   # API docs: http://localhost:8000/api/docs
```

On startup the backend:
- creates tables (if `AUTO_CREATE_TABLES=true`);
- loads and validates the seed guides;
- marks any research left "running" by a previous process as interrupted.

## 9. Database initialization and migrations

- **Local (SQLite):** nothing to do; tables are created on startup.
- **Postgres / production:**

  ```bash
  cd backend
  AUTO_CREATE_TABLES=false DATABASE_URL=postgresql://user:pass@host:5432/atlas uv run alembic upgrade head
  ```
- **New migration after model changes:**

  ```bash
  uv run alembic revision --autogenerate -m "describe change"
  ```

## 10–12. Configuring Anthropic, OpenAI, OpenRouter

Each provider is independent. Pick one as the app default, or let users bring their own key.

| Provider | `.env` | SDK path |
|---|---|---|
| Anthropic | `DEFAULT_LLM_PROVIDER=anthropic`, `DEFAULT_LLM_MODEL=claude-sonnet-5-5`, `ANTHROPIC_API_KEY=…` | `anthropic.AsyncAnthropic().messages.create` |
| OpenAI | `DEFAULT_LLM_PROVIDER=openai`, `DEFAULT_LLM_MODEL=gpt-5.5`, `OPENAI_API_KEY=…` | `openai.AsyncOpenAI().responses.create` |
| OpenRouter | `DEFAULT_LLM_PROVIDER=openrouter`, `DEFAULT_LLM_MODEL=anthropic/claude-sonnet-5.5`, `OPENROUTER_API_KEY=…` | `openai.AsyncOpenAI(base_url="https://openrouter.ai/api/v1").chat.completions.create` |

- The suggested model IDs were checked on 2026-10-20 against OpenRouter's public model list and Anthropic's model names.
- OpenRouter also offers NVIDIA Nemotron (e.g. `nvidia/nemotron-3-super-120b-a12b`).
- In the UI, **Load available models** lists live models from the provider (OpenRouter's public list, or Anthropic/OpenAI with a saved key).

## 13. How session-only BYOK works

1. The user selects a provider and model and pastes a key in **LLM settings**. The field is `type=password` and is cleared immediately after submit. Nothing is written to localStorage, sessionStorage, cookies, or URLs.
2. `POST /api/session/llm-config` validates the provider and model, optionally makes a tiny test call, and stores `{provider, model, key, created, expires}` **in server memory only**.
3. The browser receives an HttpOnly, SameSite=Lax (Secure in production), **signed opaque session ID**. The server always mints its own ID and never adopts one from the client, and it rotates the ID on every save.
4. The entry is bound to the browser's signed anonymous ID, so a copied session cookie alone can't use someone else's key.
5. Responses only ever include provider, model, source, and expiry. Keys never appear in responses, logs (a redaction filter backs this up), research runs, guides, or the database.
6. If a user's key fails or expires, the error is shown. **The app never silently falls back to its own paid key.** An expired session returns `409 llm_session_expired` until the user re-enters a key or explicitly clears it.
7. Keys are dropped on **Clear my key**, on expiry (default 60 min), or on server restart. Removing the reference does not guarantee the bytes are erased from process memory.

> In-memory sessions suit a single-process demo. Horizontally scaled deployments need a shared, encrypted, short-TTL store; see Limitations.

## 14. How to configure the search API

1. Create a key at [tavily.com](https://tavily.com).
2. Set `TAVILY_API_KEY` in `backend/.env`.

Without it, live research still works when the user enters a documentation URL ("URL mode" follows up to 6 relevant same-site links). Researching by name alone returns a clear `search_not_configured` message.

## 15. How live research works

1. **Identify the provider.** The search results and any submitted page are given to the LLM, which picks the provider and its official domains. Domains that never appeared in the results are dropped.
2. **Find documentation.** Up to 4 topic queries run: auth/registration, scopes, and review/verification/distribution. They search official domains first; other sites are labelled *secondary*.
3. **Retrieve pages.** Up to 12 pages, fetched with SSRF protection. Failures are recorded. A page that can't be fetched keeps its search snippet as *snippet only*, which never counts as documented evidence.
4. **Extract claims by topic.** The LLM returns claims with a **verbatim quote** and a source ID. Page text is wrapped as untrusted data.
5. **Probe OAuth metadata.** The pipeline requests `/.well-known/openid-configuration` and RFC 8414 metadata on official hosts. A valid document is the only source of **Tested** claims.
6. **Cross-check.** Code checks each quote against the page text. Matching ignores punctuation, but numbers and meaningful words must match exactly, so "10 weeks" never verifies "2 weeks" and "unable" never verifies "able". Quotes found in two retrieved pages become *cross-checked*. Mismatches are downgraded to *inferred* and listed.
7. **Generate and validate.** The LLM drafts the guide from the checked claims. Pydantic validates it with ≤2 retries, feeding errors back. Then deterministic rules apply:
   - approval or waiting-time conclusions without documented support become *unclear/unknown*;
   - effort is recomputed from per-step estimates;
   - a step's status is its weakest claim.
8. **Persist.** The run ends as `completed`, `partial` (evidence gaps, or the guide failed validation but the evidence was saved), or `failed` with a safe error.

## 16. Running tests

Backend:

```bash
cd backend
uv run pytest                       # 110 tests, no network or paid calls
uv run ruff check app tests ../scripts && uv run ruff format --check app tests ../scripts
uv run mypy app
```

Frontend:

```bash
cd frontend
npm test                            # 12 Vitest + Testing Library tests
npm run lint && npm run typecheck && npm run build
```

Re-check the seed guides against the live provider docs (uses the network):

```bash
cd backend && uv run python ../scripts/verify_seed_sources.py   # writes docs/seed-verification-report.md
```

## 17. How to deploy

- **Backend: Render.** `render.yaml` is a Blueprint for a single-instance FastAPI web service plus Render Postgres.
  - The start command runs `alembic upgrade head`.
  - Set `ALLOWED_ORIGINS` and `PUBLIC_APP_URL` to the Vercel URL, plus the default LLM, its key, and `TAVILY_API_KEY` in the dashboard.
  - `SESSION_SECRET` is generated.
- **Frontend: Vercel.** Import `frontend/` as the project root and set `BACKEND_URL` to the Render service URL. The `/api/*` rewrite proxies to it.
- Keep the backend at **one instance**, because BYOK sessions are in memory.

> Deployment status: see the "Deployment" note at the end of this file. It is filled in only after a deploy has actually been smoke-tested.

## 18. Security precautions

- **BYOK:**
  - keys live in server memory only, behind signed, rotating, owner-bound HttpOnly cookies;
  - keys never reach responses, logs, the database, or browser storage;
  - there is no silent fallback to the operator's key;
  - errors from provider SDKs are rewritten into fixed messages, because SDK messages can echo key fragments.
- **CSRF:**
  - state-changing `/api` requests require an `X-Atlas-CSRF` header;
  - an `Origin` header, if present, must be in `ALLOWED_ORIGINS`;
  - no CORS is enabled.
- **SSRF:**
  - http/https only, default ports, no credentials in URLs;
  - internal hostnames (`localhost`, `*.internal`, `metadata.google.internal`, …) are blocked;
  - every DNS answer must be a public address;
  - the connection goes to the validated IP with SNI/Host set to the original name, which closes the DNS-rebinding gap;
  - every redirect hop is re-validated;
  - 2 MB / 20 s limits and a content-type allowlist; nothing downloaded is executed.
- **Prompt injection:**
  - page text is wrapped in `<untrusted_source>` tags that the page can't close;
  - the model has no tools and never sees secrets;
  - outputs are schema-validated, and evidence status is decided by code.
- **Abuse limits:**
  - in-memory rate limits per browser and IP on key tests, research (stricter on the operator's key, plus a global hourly ceiling), chat, and reports.
- **Headers:**
  - `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, and `Cache-Control: no-store` on session endpoints.

## 19. Known limitations

What works without any credentials:
- Browsing, searching, and sharing the seed guides.
- Checklists and issue reports.
- Viewing evidence.
- LLM settings (except actually using a key).

What needs more:
- **Needs an LLM key** (default or BYOK): live research, refresh, and Q&A.
- **Needs `TAVILY_API_KEY`:** research by app *name*. URL-based research works without it.

What has been tested:
- **Automated:** 110 backend and 12 frontend tests, all against mocks. The SSRF fetcher was also checked against live docs.
- **Seed checks:** every one of the 79 seed claims was re-checked against the live pages (0 failures; see `docs/seed-verification-report.md`).
- **Browser:** the UI was walked through in a browser against the local stack.

**Live research with real keys:** Notion and HubSpot were researched end to end on 2026-10-20 using a free OpenRouter model. Results, spot checks, and the bugs these runs exposed are in `docs/VERIFICATION.md`. A run on a paid model, and research by app name (Tavily), have not been exercised yet.

What has not been tested:
- The OpenAI adapter against the real API. It is covered by mocked SDK tests only.
- Postgres. The Alembic migration was generated and applied on SQLite, but Postgres was not run locally (Docker was unavailable). It is exercised on the first Render deploy.

Limitations by design:
- **In-memory state:**
  - BYOK sessions, rate limits, and running research tasks are per process;
  - a restart drops keys and marks running research as interrupted;
  - Render's free tier also sleeps, which has the same effect.
- **Retrieval is not testing:**
  - a documented requirement is not a working integration;
  - the app does not create provider accounts or submit apps for review;
  - "Tested" covers only live OAuth discovery documents.
- **JavaScript-rendered docs:** may only be available as search snippets, which are never treated as documented evidence.
- **Effort is an estimate. Waiting time is shown only when documented.** No approval-probability score is produced.
- **Refreshing guides:**
  - live guides are refreshed in place, keeping no version history;
  - refreshing a seed creates a separate live guide;
  - checklist progress is per browser (anonymous), not per account.
- **Unproven elements:**
  - managed-OAuth availability per platform (e.g. Composio) is not checked;
  - guides present it as an option with no evidence.

## 20. Future improvements

- A shared, encrypted session store (e.g. Redis with short TTL) for multi-instance deployments.
- A durable job queue for research.
- Guide versioning with diffs between refreshes.
- Scheduled re-checks of seed and saved guides, flagging pages that changed.
- Check managed-OAuth availability via integration-platform APIs.
- Optional "attempt setup" agents (e.g. probing authorize endpoints with a placeholder client ID to confirm error behavior) recorded as additional Tested evidence.
- Accounts so checklists and reports follow a user across devices.
- Grow the library toward 100 providers, using the seed format plus `verify_seed_sources.py` as the quality gate.

---

### Deployment

Deployed and smoke-tested on 2026-10-20:

- **App:** https://integration-atlas-black.vercel.app (Vercel, project root `frontend/`, `BACKEND_URL` set)
- **API:** https://integration-atlas-api.onrender.com/api/health (Render free web service, Oregon)

Smoke test:
- All pages load.
- Seed guides are served through the Vercel `/api` proxy, with a `Secure; HttpOnly` cookie.
- Checklist writes succeed from the site and are rejected (403) from a foreign `Origin`.

Free-tier notes:
- The Render service sleeps when idle, so the first request can take up to a minute.
- Session keys entered in LLM settings are cleared on each restart.
