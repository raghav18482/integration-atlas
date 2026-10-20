"""SSRF-safe page retrieval and text extraction.

- Each hop is validated (scheme, host, port, resolved IPs) and redirects are
  followed manually (max 5), so a public URL cannot bounce into the network.
- The TCP connection goes to the validated IP, with Host/SNI set to the original
  hostname, which closes the DNS-rebinding gap between check and connect.
- Responses are size-capped, time-limited, and content-type restricted.
- Retrieved text is treated as untrusted data; nothing is executed.
"""

from __future__ import annotations

import asyncio
import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.security.url_validation import UnsafeURLError, check_url, resolve_public_ips

USER_AGENT = "IntegrationAtlasBot/0.1 (+research of public developer documentation)"
MAX_BYTES = 2_000_000
MAX_TEXT_CHARS = 20_000
MAX_REDIRECTS = 5
_ALLOWED_TYPES = ("text/html", "application/xhtml+xml", "text/plain", "text/markdown", "application/json")
_REDIRECTS = {301, 302, 303, 307, 308}


@dataclass
class FetchResult:
    requested_url: str
    final_url: str
    ok: bool
    blocked: bool = False
    title: str = ""
    text: str = ""
    content_type: str = ""
    http_status: int | None = None
    error: str | None = None
    raw: str = ""


def default_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(15.0, connect=5.0),
        follow_redirects=False,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.5",
        },
        trust_env=False,
    )


def _pinned_url(scheme: str, ip: str, path_and_query: str) -> str:
    host = f"[{ip}]" if isinstance(ipaddress.ip_address(ip), ipaddress.IPv6Address) else ip
    return f"{scheme}://{host}{path_and_query}"


def extract_text(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "lxml")
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    for tag in soup(
        ["script", "style", "noscript", "svg", "nav", "footer", "header", "form", "iframe", "template"]
    ):
        tag.decompose()
    root = soup.find("main") or soup.find("article") or soup.select_one('[role="main"]') or soup.body or soup
    if not title:
        h1 = root.find("h1") if hasattr(root, "find") else None
        title = h1.get_text(" ", strip=True) if h1 else ""
    text = root.get_text("\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return title[:300], text[:MAX_TEXT_CHARS]


async def fetch_document(
    url: str,
    client: httpx.AsyncClient,
    *,
    max_bytes: int = MAX_BYTES,
    total_timeout: float = 20.0,
) -> FetchResult:
    try:
        async with asyncio.timeout(total_timeout):
            return await _fetch(url, client, max_bytes)
    except TimeoutError:
        return FetchResult(requested_url=url, final_url=url, ok=False, error="Timed out")


async def _fetch(url: str, client: httpx.AsyncClient, max_bytes: int) -> FetchResult:
    current = url
    for _hop in range(MAX_REDIRECTS + 1):
        try:
            checked = check_url(current)
            ips = await resolve_public_ips(checked.host)
        except UnsafeURLError as exc:
            return FetchResult(requested_url=url, final_url=current, ok=False, blocked=True, error=str(exc))

        request_url = _pinned_url(checked.scheme, ips[0], checked.path_and_query)
        extensions = {"sni_hostname": checked.host} if checked.scheme == "https" else {}
        try:
            async with client.stream(
                "GET", request_url, headers={"Host": checked.host}, extensions=extensions
            ) as resp:
                if resp.status_code in _REDIRECTS:
                    location = resp.headers.get("location")
                    if not location:
                        return FetchResult(
                            url,
                            checked.url,
                            False,
                            http_status=resp.status_code,
                            error="Redirect without location",
                        )
                    current = urljoin(checked.url, location)
                    continue
                if resp.status_code >= 400:
                    return FetchResult(
                        url,
                        checked.url,
                        False,
                        http_status=resp.status_code,
                        error=f"HTTP {resp.status_code}",
                    )
                content_type = resp.headers.get("content-type", "").split(";")[0].strip().lower()
                if content_type and not content_type.startswith(_ALLOWED_TYPES):
                    return FetchResult(
                        url,
                        checked.url,
                        False,
                        http_status=resp.status_code,
                        content_type=content_type,
                        error=f"Unsupported content type {content_type}",
                    )
                chunks: list[bytes] = []
                size = 0
                async for chunk in resp.aiter_bytes():
                    size += len(chunk)
                    if size > max_bytes:
                        chunks.append(chunk[: max(0, max_bytes - (size - len(chunk)))])
                        break
                    chunks.append(chunk)
                body = b"".join(chunks).decode(resp.encoding or "utf-8", errors="replace")
        except httpx.HTTPError as exc:
            return FetchResult(url, checked.url, False, error=f"Network error ({type(exc).__name__})")

        if content_type in ("text/html", "application/xhtml+xml") or (
            not content_type and "<html" in body[:500].lower()
        ):
            title, text = extract_text(body)
        else:
            title, text = "", body[:MAX_TEXT_CHARS]
        if not text.strip():
            return FetchResult(
                url,
                checked.url,
                False,
                http_status=200,
                content_type=content_type,
                error="Page had no extractable text (may require JavaScript)",
            )
        return FetchResult(
            requested_url=url,
            final_url=checked.url,
            ok=True,
            title=title,
            text=text,
            content_type=content_type,
            http_status=200,
            raw=body[:MAX_BYTES],
        )
    return FetchResult(url, current, False, error="Too many redirects")
