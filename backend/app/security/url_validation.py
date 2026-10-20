"""SSRF protection for user-submitted and discovered URLs.

Rules: http/https only, default ports only, no credentials in the URL, no
internal hostnames, and every DNS answer must be a public (globally routable)
address. Fetchers then connect to the validated IP (see document_fetcher) and
re-validate each redirect hop.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

_BLOCKED_HOSTS = {
    "localhost",
    "localhost.localdomain",
    "metadata",
    "metadata.google.internal",
    "instance-data",
    "instance-data.ec2.internal",
}
_BLOCKED_SUFFIXES = (
    ".localhost",
    ".local",
    ".internal",
    ".localdomain",
    ".home.arpa",
    ".lan",
    ".intranet",
    ".corp",
)


class UnsafeURLError(ValueError):
    pass


@dataclass(frozen=True)
class CheckedURL:
    url: str
    scheme: str
    host: str
    port: int
    path_and_query: str


def ip_is_public(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return bool(
        ip.is_global
        and not ip.is_multicast
        and not ip.is_private
        and not ip.is_loopback
        and not ip.is_link_local
        and not ip.is_reserved
        and not ip.is_unspecified
    )


def check_url(raw: str) -> CheckedURL:
    raw = (raw or "").strip()
    if not raw or len(raw) > 2048:
        raise UnsafeURLError("URL is empty or too long.")
    try:
        parts = urlsplit(raw)
    except ValueError:
        raise UnsafeURLError("URL could not be parsed.") from None
    scheme = parts.scheme.lower()
    if scheme not in ("http", "https"):
        raise UnsafeURLError("Only http and https URLs are allowed.")
    if parts.username or parts.password or "@" in parts.netloc:
        raise UnsafeURLError("URLs with embedded credentials are not allowed.")
    try:
        port = parts.port
    except ValueError:
        raise UnsafeURLError("URL has an invalid port.") from None
    default_port = 443 if scheme == "https" else 80
    if port not in (None, default_port):
        raise UnsafeURLError("Only default ports (80/443) are allowed.")
    host = (parts.hostname or "").rstrip(".").lower()
    if not host:
        raise UnsafeURLError("URL has no hostname.")
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError:
        raise UnsafeURLError("URL hostname is invalid.") from None
    if host in _BLOCKED_HOSTS or host.endswith(_BLOCKED_SUFFIXES):
        raise UnsafeURLError("Internal hostnames are not allowed.")
    is_ip_literal = True
    try:
        ipaddress.ip_address(host)
    except ValueError:
        is_ip_literal = False
    if is_ip_literal and not ip_is_public(host):
        raise UnsafeURLError("Private, loopback, and link-local addresses are not allowed.")
    if not is_ip_literal and "." not in host:
        raise UnsafeURLError("Single-label hostnames are not allowed.")
    path_and_query = urlunsplit(("", "", parts.path or "/", parts.query, ""))
    normalized = urlunsplit((scheme, host, parts.path or "/", parts.query, ""))
    return CheckedURL(
        url=normalized, scheme=scheme, host=host, port=default_port, path_and_query=path_and_query
    )


async def resolve_public_ips(host: str) -> list[str]:
    """Resolve a hostname and require every answer to be a public address."""
    try:
        ipaddress.ip_address(host)
        candidates = [host]
    except ValueError:
        loop = asyncio.get_running_loop()
        try:
            infos = await asyncio.wait_for(loop.getaddrinfo(host, None, type=socket.SOCK_STREAM), timeout=5.0)
        except (TimeoutError, socket.gaierror, OSError):
            raise UnsafeURLError("Hostname could not be resolved.") from None
        candidates = sorted({str(info[4][0]) for info in infos})
    if not candidates:
        raise UnsafeURLError("Hostname did not resolve to any address.")
    if not all(ip_is_public(ip) for ip in candidates):
        raise UnsafeURLError("Hostname resolves to a private or reserved address.")
    return candidates


async def validate_public_url(raw: str) -> CheckedURL:
    checked = check_url(raw)
    await resolve_public_ips(checked.host)
    return checked
