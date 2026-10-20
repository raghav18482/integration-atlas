from __future__ import annotations

import socket

import httpx
import pytest

from app.security import url_validation
from app.security.url_validation import UnsafeURLError, check_url, ip_is_public, resolve_public_ips
from app.services import document_fetcher
from app.services.document_fetcher import fetch_document


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/admin",
        "http://127.0.0.1/",
        "http://10.0.0.5/",
        "http://192.168.1.1/",
        "http://172.16.0.1/",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/",
        "http://[fd00::1]/",
        "http://[::ffff:127.0.0.1]/",
        "http://100.64.0.1/",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://printer.local/",
        "file:///etc/passwd",
        "gopher://example.com/",
        "ftp://example.com/",
        "https://user:pass@example.com/",
        "https://example.com:8443/",
        "http://intranet/",
        "",
    ],
)
def test_unsafe_urls_rejected(url):
    with pytest.raises(UnsafeURLError):
        check_url(url)


def test_public_url_accepted_and_normalized():
    checked = check_url("HTTPS://Docs.Example.com/oauth#section")
    assert checked.url == "https://docs.example.com/oauth"
    assert checked.port == 443


def test_ip_classification():
    assert ip_is_public("8.8.8.8")
    for ip in ("10.1.1.1", "127.0.0.1", "169.254.169.254", "::1", "0.0.0.0", "224.0.0.1"):
        assert not ip_is_public(ip)


async def test_dns_answers_must_all_be_public(monkeypatch):
    async def fake_getaddrinfo(host, port, type=0):  # noqa: A002
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("10.0.0.7", 0)),
        ]

    loop = __import__("asyncio").get_running_loop()
    monkeypatch.setattr(loop, "getaddrinfo", fake_getaddrinfo)
    with pytest.raises(UnsafeURLError, match="private"):
        await resolve_public_ips("rebind.example.com")


def _public_dns(monkeypatch, mapping: dict[str, str]):
    async def fake_resolve(host: str):
        if host in mapping:
            return [mapping[host]]
        return await url_validation.resolve_public_ips(host)

    monkeypatch.setattr(document_fetcher, "resolve_public_ips", fake_resolve)


async def test_redirect_to_internal_address_is_blocked(monkeypatch):
    _public_dns(monkeypatch, {"docs.example.com": "93.184.216.34"})

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["host"] == "docs.example.com"
        return httpx.Response(302, headers={"location": "http://169.254.169.254/latest/meta-data/"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await fetch_document("https://docs.example.com/start", client)
    assert not result.ok and result.blocked
    assert result.text == ""


async def test_connects_to_validated_ip_with_original_host(monkeypatch):
    _public_dns(monkeypatch, {"docs.example.com": "93.184.216.34"})
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text="<html><title>T</title><main>OAuth guide</main></html>",
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await fetch_document("https://docs.example.com/oauth", client)
    assert result.ok and result.title == "T" and "OAuth guide" in result.text
    assert seen == ["https://93.184.216.34/oauth"]


async def test_disallowed_content_type_and_errors_are_not_fabricated(monkeypatch):
    _public_dns(monkeypatch, {"docs.example.com": "93.184.216.34"})

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/bin":
            return httpx.Response(
                200, headers={"content-type": "application/octet-stream"}, content=b"\x00\x01"
            )
        return httpx.Response(503)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        binary = await fetch_document("https://docs.example.com/bin", client)
        down = await fetch_document("https://docs.example.com/down", client)
    assert not binary.ok and "content type" in (binary.error or "")
    assert not down.ok and down.error == "HTTP 503" and down.text == ""


async def test_response_size_is_capped(monkeypatch):
    _public_dns(monkeypatch, {"docs.example.com": "93.184.216.34"})
    big = "<html><main>" + ("x" * 50_000) + "</main></html>"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "text/html"}, text=big)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await fetch_document("https://docs.example.com/big", client, max_bytes=1000)
    assert len(result.raw) <= 1000
