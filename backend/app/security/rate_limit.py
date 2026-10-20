"""Small in-memory sliding-window rate limiter (single-process demo scope)."""

from __future__ import annotations

import math
import time
from collections import deque
from collections.abc import Callable

from app.errors import AppError


class RateLimitExceeded(AppError):
    def __init__(self, retry_after: int) -> None:
        super().__init__(
            "rate_limited",
            f"Too many requests. Try again in about {retry_after} seconds.",
            status_code=429,
        )
        self.retry_after = retry_after


class RateLimiter:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}

    def check(self, key: str, limit: int, window_seconds: float) -> None:
        now = self._clock()
        hits = self._hits.setdefault(key, deque())
        while hits and hits[0] <= now - window_seconds:
            hits.popleft()
        if len(hits) >= limit:
            retry_after = max(1, math.ceil(hits[0] + window_seconds - now))
            raise RateLimitExceeded(retry_after)
        hits.append(now)
        if len(self._hits) > 50_000:  # bound memory under abuse
            self._hits = {k: v for k, v in self._hits.items() if v}

    def reset(self) -> None:
        self._hits.clear()
