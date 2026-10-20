"""Web search behind a small protocol. Tavily is the configured implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlsplit

import httpx

TAVILY_URL = "https://api.tavily.com/search"


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    score: float = 0.0

    @property
    def domain(self) -> str:
        return (urlsplit(self.url).hostname or "").lower()


class SearchError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class SearchClient(Protocol):
    async def search(
        self, query: str, *, include_domains: list[str] | None = None, max_results: int = 5
    ) -> list[SearchResult]: ...


class TavilySearch:
    def __init__(self, api_key: str, client: httpx.AsyncClient | None = None) -> None:
        self._key = api_key
        self._client = client

    async def search(
        self, query: str, *, include_domains: list[str] | None = None, max_results: int = 5
    ) -> list[SearchResult]:
        payload: dict = {
            "query": query[:400],
            "max_results": max(1, min(max_results, 10)),
            "search_depth": "basic",
            "include_answer": False,
            "include_raw_content": False,
        }
        if include_domains:
            payload["include_domains"] = include_domains[:10]
        owns = self._client is None
        client = self._client or httpx.AsyncClient(timeout=20.0, trust_env=False)
        try:
            resp = await client.post(
                TAVILY_URL, json=payload, headers={"Authorization": f"Bearer {self._key}"}
            )
        except httpx.HTTPError as exc:
            raise SearchError(f"Search request failed ({type(exc).__name__}).") from None
        finally:
            if owns:
                await client.aclose()
        if resp.status_code in (401, 403):
            raise SearchError("The search API rejected the configured key.")
        if resp.status_code == 429:
            raise SearchError("The search API rate limit or quota was reached.")
        if resp.status_code >= 400:
            raise SearchError(f"The search API returned HTTP {resp.status_code}.")
        try:
            items = resp.json().get("results", [])
        except ValueError:
            raise SearchError("The search API returned an unreadable response.") from None
        results = []
        for item in items:
            url = str(item.get("url") or "")
            if not url.startswith(("http://", "https://")):
                continue
            results.append(
                SearchResult(
                    title=str(item.get("title") or url)[:300],
                    url=url[:2048],
                    snippet=str(item.get("content") or "")[:1500],
                    score=float(item.get("score") or 0.0),
                )
            )
        return results
