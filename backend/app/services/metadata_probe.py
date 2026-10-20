"""Live OAuth metadata probe: the only source of `tested` claims.

We request standard discovery documents (OpenID Connect Discovery 1.0 and RFC 8414)
on the provider's official hosts. A valid document is a real, machine-checked
observation of the provider's OAuth endpoints, recorded with what was fetched
and when. Absence of a document proves nothing and is not reported as a claim.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.services.document_fetcher import FetchResult

FetchFn = Callable[..., Awaitable[FetchResult]]

WELL_KNOWN_PATHS = ("/.well-known/openid-configuration", "/.well-known/oauth-authorization-server")
_AUTH_SUBDOMAINS = ("accounts", "auth", "login", "oauth")


@dataclass
class ProbeResult:
    url: str
    fetched_at: datetime
    issuer: str
    authorization_endpoint: str | None
    token_endpoint: str | None
    scopes_supported: list[str] = field(default_factory=list)
    grant_types_supported: list[str] = field(default_factory=list)
    code_challenge_methods_supported: list[str] = field(default_factory=list)
    raw_excerpt: str = ""


# Shared hosting / platform domains: a subdomain here does not make the parent official.
SHARED_HOSTING_SUFFIXES = (
    "github.io",
    "readme.io",
    "gitbook.io",
    "medium.com",
    "notion.site",
    "vercel.app",
    "netlify.app",
    "herokuapp.com",
    "zendesk.com",
    "freshdesk.com",
    "atlassian.net",
    "document360.io",
    "mintlify.app",
    "stoplight.io",
    "postman.com",
    "apiary.io",
    "blogspot.com",
    "wordpress.com",
    "substack.com",
    "dev.to",
    "stackoverflow.com",
    "reddit.com",
    "youtube.com",
    "amazonaws.com",
    "cloudfront.net",
    "pages.dev",
    "web.app",
    "firebaseapp.com",
    "azurewebsites.net",
)


def registrable_domain(host: str) -> str:
    parts = host.lower().strip(".").split(".")
    if len(parts) >= 3 and len(parts[-1]) == 2 and parts[-2] in {"co", "com", "org", "net", "gov", "ac"}:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def is_shared_hosting(host: str) -> bool:
    host = host.lower()
    return any(host == s or host.endswith("." + s) for s in SHARED_HOSTING_SUFFIXES)


def official_roots(official_domains: list[str]) -> list[str]:
    """Hosts that count as official: the listed hosts, plus their registrable parent
    unless the host lives on a shared hosting platform."""
    roots: list[str] = []
    for domain in official_domains:
        for candidate in (domain.lower(), registrable_domain(domain)):
            if candidate == registrable_domain(domain) and is_shared_hosting(domain):
                continue
            if candidate not in roots:
                roots.append(candidate)
    return roots


def host_is_official(host: str, roots: list[str]) -> bool:
    host = host.lower()
    return any(host == r or host.endswith("." + r) for r in roots)


def candidate_hosts(official_domains: list[str], limit: int = 4) -> list[str]:
    hosts: list[str] = []
    for domain in official_domains:
        expansions = [domain]
        if not is_shared_hosting(domain):
            base = registrable_domain(domain)
            expansions += [base, *(f"{sub}.{base}" for sub in _AUTH_SUBDOMAINS)]
        for host in expansions:
            if host not in hosts:
                hosts.append(host)
    return hosts[: limit * 3]


def _str_list(value: object, limit: int = 40) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(v)[:120] for v in value if isinstance(v, str | int)][:limit]


async def probe_oauth_metadata(
    official_domains: list[str], fetch: FetchFn, *, max_requests: int = 10
) -> list[ProbeResult]:
    results: list[ProbeResult] = []
    seen_issuers: set[str] = set()
    requests = 0
    for host in candidate_hosts(official_domains):
        for path in WELL_KNOWN_PATHS:
            if requests >= max_requests:
                return results
            requests += 1
            url = f"https://{host}{path}"
            fetched = await fetch(url, max_bytes=200_000, total_timeout=8.0)
            if not fetched.ok:
                continue
            try:
                doc = json.loads(fetched.raw or fetched.text)
            except ValueError:
                continue
            if not isinstance(doc, dict) or not doc.get("issuer") or not doc.get("authorization_endpoint"):
                continue
            issuer = str(doc["issuer"])[:300]
            if issuer in seen_issuers:
                continue
            seen_issuers.add(issuer)
            results.append(
                ProbeResult(
                    url=fetched.final_url,
                    fetched_at=datetime.now(UTC),
                    issuer=issuer,
                    authorization_endpoint=str(doc.get("authorization_endpoint"))[:500],
                    token_endpoint=str(doc.get("token_endpoint"))[:500]
                    if doc.get("token_endpoint")
                    else None,
                    scopes_supported=_str_list(doc.get("scopes_supported")),
                    grant_types_supported=_str_list(doc.get("grant_types_supported")),
                    code_challenge_methods_supported=_str_list(doc.get("code_challenge_methods_supported")),
                    raw_excerpt=(fetched.raw or fetched.text)[:4000],
                )
            )
            break  # one valid document per host is enough
    return results
