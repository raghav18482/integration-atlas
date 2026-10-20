# Verification log

What was checked, what was corrected, and what remains uncertain. Dates are from the build session on 2026-10-20.

## 1. Seed guides vs. live official documentation

**Method.**
1. Each seed claim was written from text fetched from the provider's official pages.
2. `scripts/verify_seed_sources.py` re-fetches every source with the app's SSRF-safe fetcher.
3. It checks each claim's quote using the same matcher the research pipeline uses.
4. It re-reads the live OAuth discovery document for `tested` claims.

**Result.** 79 claims across 22 sources, 0 failures. Full table: [`seed-verification-report.md`](seed-verification-report.md).

| Guide | Claims | Documented | Cross-checked | Tested | Inferred | Unknown |
|---|---|---|---|---|---|---|
| Slack | 24 | 21 | 2 | 0 | 0 | 1 |
| GitHub | 26 | 22 | 2 | 0 | 1 | 1 |
| Google | 29 | 24 | 1 | 3 | 0 | 1 |

### Corrections made while curating

| What I expected | What the sources said | Change |
|---|---|---|
| GitHub Marketplace listing needs 100+ installs and listing verification | Those requirements appear **only under "Requirements for paid apps"**. Free listings follow the general requirements. | The seed marks both as paid-listing requirements, with a note on the claim. |
| Slack Marketplace docs at `api.slack.com/docs/slack-marketplace` | That URL returns 404. Slack docs moved to `docs.slack.dev`, and old `api.slack.com` links redirect. | All Slack sources use the current `docs.slack.dev` URLs. |
| A GitHub doc stating public apps need no review | The likely page (`…/making-a-github-app-public-or-private`) returns 404. The registration page shows the "Any account" option but never states that no review exists. | Recorded as an **inferred** claim (C26) and an "unknown" blocker, not as documented fact. |
| Slack history rate limits are generic | Since 2025-05-29, **new installs of commercially distributed non-Marketplace apps** get 1 request/minute and 15 objects on `conversations.history`/`replies`. Internal apps are exempt. | Added as a cross-checked, high-impact blocker. This is the most important nuance for AI agents that read Slack history. |
| Google restricted-scope verification has a published duration | Google only says it "can potentially take several weeks" because of the third-party assessment. No assessor duration or cost is documented. | External wait is labelled *estimated* ("several weeks+"), and the assessment duration and cost are an **unknown**. |

### Could not verify

- Whether a given scope set will be approved by Slack, Google, or GitHub. That is a review outcome, and no score is given.
- Duration and cost of Google's CASA security assessment.
- How long GitHub Marketplace publisher/listing verification takes.
- Which integration platforms offer a managed OAuth app for each provider. Composio's directory page lists toolkits, but the page we fetched doesn't separate the managed and bring-your-own groups for a specific app. The guides show the managed option without evidence and say so.

## 2. The evidence checker itself

The quote matcher decides whether a claim is "Documented". An early version used fuzzy matching (rapidfuzz `partial_ratio ≥ 92`), and testing against the Slack review page showed it was **unsafe**:

| Probe | Early matcher | Final matcher |
|---|---|---|
| "functional review takes up to **2** weeks" (page says 10) | accepted ✗ | rejected ✓ |
| "preliminary review takes up to **5** business days" (page says 10) | accepted ✗ | rejected ✓ |
| "We are **able** to skip or accelerate the review" (page says *unable*) | accepted ✗ | rejected ✓ |
| Real quote with punctuation and line-break differences | accepted ✓ | accepted ✓ |
| Real quote missing a few filler words ("the") | accepted ✓ | accepted ✓ |

**Fix.** The final matcher works as follows:
- Exact match on letters and digits; punctuation and whitespace are ignored.
- Near matches are allowed only for quotes of 40+ characters.
- Every word that differs between the quote and the page must be a filler word. Numbers, negations, and substantive words must match exactly.

These cases are regression tests in `backend/tests/test_evidence.py`.

## 3. Pipeline behavior (automated, mocked)

`backend/tests/test_research_workflow.py` runs the full pipeline with fake search, fetch, and LLM, and checks:
- A claim whose quote the model invented is downgraded to *inferred*, loses its source link, and is listed in the report.
- Domains the model proposes that never appeared in search results are dropped.
- A page that fails to load keeps only its search snippet, which never counts as documented.
- A drafted "known" waiting time with no supporting claim is coerced to *unknown*.
- Effort is recomputed from steps.
- If guide generation fails validation, the evidence is still saved as a *partial* guide.
- A rejected user key fails the run with a safe error and never touches the operator's key.
- Page content trying to close the `<untrusted_source>` wrapper is neutralised.

## 4. Live research with real keys (2026-10-20)

**Setup.**
- No Tavily key was available, so every run started from an official docs URL ("URL mode" follows up to 6 relevant same-site links).
- The OpenRouter and Anthropic accounts both had **no credit**:
  - OpenRouter returned 402 for Claude Sonnet requests.
  - Anthropic returned *"credit balance is too low"*, although the key itself was valid (`models.list` worked).
- The runs therefore used OpenRouter's **free** `minimax/minimax-m3.1-flash:free`, entered as a session-only key through the BYOK endpoint.

### Results

| App | Time | Pages | Claims | Documented | Quote mismatches caught | Guide |
|---|---|---|---|---|---|---|
| Notion (`developers.notion.com/docs/authorization`) | 141 s | 7/7 | 73 | 53 (+1 cross-checked) | 1 | complete · approval *unclear* · wait *unknown* · 5.4–10.1 h |
| HubSpot (`…/legacy-apps/authentication/working-with-oauth`) | 135 s | 5/7 | 66 | 47 | 1 | complete · approval *unclear* · wait *unknown* · 12.2–22.9 h |

### Spot checks against the pages

**Notion.**
- The guide states that the OAuth Authorization URL appears only after a public connection is submitted for review, and that Notion documents no timeline for that review. This matches the source.
- Hence approval *unclear* and wait *unknown* rather than a guess.
- Marketplace review is quoted as "within 5-10 business days".
- "Installation scope can't be changed after creation", "only *Any workspace* connections can be listed", and "each member must authorize separately" are all quoted verbatim.

**HubSpot.**
- "Installers must be Super Admins or have Marketplace Access permission" and the unverified-domain / unreviewed-app install banners are quoted verbatim.
- Approval is *unclear* because HubSpot's review-process page was not among the followed links. That is an honest gap, not a finding that no review exists.

### Problems found by the live runs, and fixes

| Problem | Fix |
|---|---|
| Comma-separated `ALLOWED_ORIGINS` (the documented `.env` format) crashed startup: pydantic-settings parsed it as JSON | `NoDecode` + test loading `.env.example` and a real env file |
| Backend crashed on any restart with an existing DB: re-saving a guide inserted new claim rows before deleting old ones (unique constraint) | Clear and flush before re-inserting; restart test |
| Anthropic "credit balance too low" (HTTP 400) was shown as "rejected the request" | Mapped to `llm_insufficient_credits`; test |
| Free reasoning model (Nemotron) returned empty content after ~3.5 min on large prompts | OpenRouter calls request `reasoning: {effort: low, exclude: true}`; an empty or timed-out answer on one topic is now a warning, not a fatal error (credential and credit errors still stop the run) |
| Weaker model kept producing invalid `responsible` labels and failed validation 3× | Pre-validation label repair: close variants are fixed, unknown values become conservative defaults, and every repair is listed in the guide's verification report |
| A topic that returned **zero** claims still yielded "Evidence complete" | Empty topics record an explicit unknown, show a warning on the research screen, and mark the guide *Incomplete evidence*; test |
| URL mode followed login/signup links (their paths contain "auth") | Account pages are skipped; "Sign in with X" docs are kept |

### Still unverified

- A full run on a paid model (Claude Sonnet via OpenRouter or Anthropic). Blocked on account credit.
- Research by app *name*. Needs `TAVILY_API_KEY`.
- **Run-to-run variance.** Two HubSpot runs on the same pages gave overall approval *conditional* then *unclear*, and one free-model run returned nothing for the review topic. The evidence rules keep conclusions conservative, but wording and coverage vary between runs.
