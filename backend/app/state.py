"""Process-wide singletons (single-process demo scope)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from app.config import Settings
from app.db.session import Database
from app.security.rate_limit import RateLimiter
from app.security.session_manager import CookieSigner, LLMSessionStore


@dataclass
class AppState:
    settings: Settings
    db: Database
    sessions: LLMSessionStore
    signer: CookieSigner
    limiter: RateLimiter = field(default_factory=RateLimiter)
    # Strong references to running research tasks so they are not garbage-collected.
    tasks: set[asyncio.Task] = field(default_factory=set)


def build_state(settings: Settings) -> AppState:
    return AppState(
        settings=settings,
        db=Database(settings.database_url),
        sessions=LLMSessionStore(ttl_seconds=settings.byok_ttl_minutes * 60),
        signer=CookieSigner(settings.session_secret.get_secret_value()),
    )
