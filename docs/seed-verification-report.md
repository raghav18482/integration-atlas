# Seed verification report

Generated 2026-10-19 22:35 UTC by `scripts/verify_seed_sources.py`.

Each claim's quote is matched against the live text of its cited source(s), using the same matcher the research pipeline uses. `tested` claims are re-checked against the live discovery document.

## GitHub (`github`)

| Source | Status | URL |
|---|---|---|
| S1 | retrieved | https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/differences-between-github-apps-and-oauth-apps |
| S2 | retrieved | https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/registering-a-github-app |
| S3 | retrieved | https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/creating-an-oauth-app |
| S4 | retrieved | https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps |
| S5 | retrieved | https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps |
| S6 | retrieved | https://docs.github.com/en/apps/github-marketplace/github-marketplace-overview/about-github-marketplace-for-apps |
| S7 | retrieved | https://docs.github.com/en/apps/github-marketplace/creating-apps-for-github-marketplace/requirements-for-listing-an-app |

| Claim | Status | Result |
|---|---|---|
| C1 | officially_documented | quote found in S3 |
| C2 | cross_checked | quote found in S1 |
| C3 | officially_documented | quote found in S1 |
| C4 | officially_documented | quote found in S1 |
| C5 | officially_documented | quote found in S4 |
| C6 | cross_checked | quote found in S2, S3 |
| C7 | officially_documented | quote found in S2 |
| C8 | officially_documented | quote found in S2 |
| C9 | officially_documented | quote found in S1 |
| C10 | officially_documented | quote found in S1 |
| C11 | officially_documented | quote found in S5 |
| C12 | officially_documented | quote found in S1 |
| C13 | officially_documented | quote found in S1 |
| C14 | officially_documented | quote found in S4 |
| C15 | officially_documented | quote found in S4 |
| C16 | officially_documented | quote found in S1 |
| C17 | officially_documented | quote found in S1 |
| C18 | officially_documented | quote found in S1 |
| C19 | officially_documented | quote found in S6 |
| C20 | officially_documented | quote found in S7 |
| C21 | officially_documented | quote found in S7 |
| C22 | officially_documented | quote found in S7 |
| C23 | officially_documented | quote found in S6 |
| C24 | officially_documented | quote found in S3 |
| C25 | unknown | no quote (status is not evidence) |
| C26 | inferred | no quote (status is not evidence) |

## Google (Gmail & Calendar APIs) (`google`)

| Source | Status | URL |
|---|---|---|
| S1 | retrieved | https://developers.google.com/identity/protocols/oauth2 |
| S2 | retrieved | https://developers.google.com/identity/protocols/oauth2/web-server |
| S3 | retrieved | https://support.google.com/cloud/answer/15549945 |
| S4 | retrieved | https://developers.google.com/identity/protocols/oauth2/production-readiness/sensitive-scope-verification |
| S5 | retrieved | https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification |
| S6 | retrieved | https://support.google.com/cloud/answer/13463073 |
| S7 | retrieved | https://support.google.com/cloud/answer/7454865 |
| S8 | retrieved | https://accounts.google.com/.well-known/openid-configuration |

| Claim | Status | Result |
|---|---|---|
| C1 | officially_documented | quote found in S1 |
| C2 | officially_documented | quote found in S1 |
| C3 | officially_documented | quote found in S2 |
| C4 | officially_documented | quote found in S1 |
| C5 | officially_documented | quote found in S1 |
| C6 | officially_documented | quote found in S3 |
| C7 | officially_documented | quote found in S3 |
| C8 | officially_documented | quote found in S3 |
| C9 | cross_checked | quote found in S6 |
| C10 | officially_documented | quote found in S6 |
| C11 | officially_documented | quote found in S6 |
| C12 | officially_documented | quote found in S4 |
| C13 | officially_documented | quote found in S4 |
| C14 | officially_documented | quote found in S4 |
| C15 | officially_documented | quote found in S5 |
| C16 | officially_documented | quote found in S5 |
| C17 | officially_documented | quote found in S5 |
| C18 | officially_documented | quote found in S5 |
| C19 | officially_documented | quote found in S5 |
| C20 | officially_documented | quote found in S5 |
| C21 | officially_documented | quote found in S7 |
| C22 | tested | re-tested: values present in live document |
| C23 | tested | re-tested: values present in live document |
| C24 | officially_documented | quote found in S3 |
| C25 | unknown | no quote (status is not evidence) |
| C26 | officially_documented | quote found in S5 |
| C27 | officially_documented | quote found in S6 |
| C28 | officially_documented | quote found in S2 |
| C29 | tested | re-tested: values present in live document |

## Slack (`slack`)

| Source | Status | URL |
|---|---|---|
| S1 | retrieved | https://docs.slack.dev/authentication/installing-with-oauth/ |
| S2 | retrieved | https://docs.slack.dev/app-management/distribution/ |
| S3 | retrieved | https://docs.slack.dev/slack-marketplace/slack-marketplace-review-guide/ |
| S4 | retrieved | https://docs.slack.dev/slack-marketplace/slack-marketplace-app-guidelines-and-requirements/ |
| S5 | retrieved | https://docs.slack.dev/changelog/2025/05/29/rate-limit-changes-for-non-marketplace-apps/ |
| S6 | retrieved | https://docs.slack.dev/apis/web-api/rate-limits/ |
| S7 | retrieved | https://docs.slack.dev/authentication/tokens/ |

| Claim | Status | Result |
|---|---|---|
| C1 | officially_documented | quote found in S1 |
| C2 | officially_documented | quote found in S1 |
| C3 | officially_documented | quote found in S1 |
| C4 | officially_documented | quote found in S1 |
| C5 | officially_documented | quote found in S1 |
| C6 | officially_documented | quote found in S1 |
| C7 | officially_documented | quote found in S7 |
| C8 | officially_documented | quote found in S2 |
| C9 | officially_documented | quote found in S2 |
| C10 | officially_documented | quote found in S2 |
| C11 | officially_documented | quote found in S2 |
| C12 | officially_documented | quote found in S2 |
| C13 | cross_checked | quote found in S3 |
| C14 | officially_documented | quote found in S3 |
| C15 | officially_documented | quote found in S3 |
| C16 | officially_documented | quote found in S3 |
| C17 | officially_documented | quote found in S3 |
| C18 | officially_documented | quote found in S4 |
| C19 | cross_checked | quote found in S5 |
| C20 | officially_documented | quote found in S5 |
| C21 | officially_documented | quote found in S4 |
| C22 | officially_documented | quote found in S3 |
| C23 | officially_documented | quote found in S3 |
| C24 | unknown | no quote (status is not evidence) |

**Failures: 0**
