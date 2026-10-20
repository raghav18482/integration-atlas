"""Session-only BYOK storage.

- API keys live only in this process's memory, keyed by an opaque, server-minted,
  signed session ID. They are never written to the database, logs, or responses.
- The browser holds the signed ID in an HttpOnly cookie, never the key.
- A new session ID is minted on every save (no fixation) and entries are bound to
  the anonymous client ID, so one cookie alone cannot read another user's entry.
- Entries expire after a fixed TTL. Deleting the reference does not guarantee that
  the bytes are physically erased from process memory.
- A server restart clears every entry. Not suitable for multi-instance deployments
  without a shared encrypted store.
"""

from __future__ import annotations

import asyncio
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from itsdangerous import BadSignature, URLSafeSerializer
from pydantic import SecretStr

LLM_COOKIE = "atlas_llm"
UID_COOKIE = "atlas_uid"
UID_MAX_AGE = 60 * 60 * 24 * 365


@dataclass
class SessionLLMEntry:
    owner_uid: str
    provider_id: str
    model: str
    api_key: SecretStr = field(repr=False)
    created_at: float
    expires_at: float
    verified: bool


class CookieSigner:
    def __init__(self, secret: str) -> None:
        self._llm = URLSafeSerializer(secret, salt="atlas-llm-session")
        self._uid = URLSafeSerializer(secret, salt="atlas-anon-client")

    def sign_session(self, sid: str) -> str:
        return self._llm.dumps(sid)

    def unsign_session(self, value: str | None) -> str | None:
        return self._unsign(self._llm, value)

    def sign_uid(self, uid: str) -> str:
        return self._uid.dumps(uid)

    def unsign_uid(self, value: str | None) -> str | None:
        return self._unsign(self._uid, value)

    @staticmethod
    def _unsign(serializer: URLSafeSerializer, value: str | None) -> str | None:
        if not value or len(value) > 256:
            return None
        try:
            loaded = serializer.loads(value)
        except BadSignature:
            return None
        return loaded if isinstance(loaded, str) and 20 <= len(loaded) <= 64 else None


def new_opaque_id() -> str:
    return secrets.token_urlsafe(32)


class LLMSessionStore:
    def __init__(self, ttl_seconds: int, clock: Callable[[], float] = time.time) -> None:
        self._ttl = ttl_seconds
        self._clock = clock
        self._entries: dict[str, SessionLLMEntry] = {}
        self._lock = asyncio.Lock()

    @property
    def ttl_seconds(self) -> int:
        return self._ttl

    async def create(
        self,
        *,
        owner_uid: str,
        provider_id: str,
        model: str,
        api_key: SecretStr,
        verified: bool,
        replace_sid: str | None = None,
    ) -> tuple[str, SessionLLMEntry]:
        now = self._clock()
        entry = SessionLLMEntry(
            owner_uid=owner_uid,
            provider_id=provider_id,
            model=model,
            api_key=api_key,
            created_at=now,
            expires_at=now + self._ttl,
            verified=verified,
        )
        sid = new_opaque_id()
        async with self._lock:
            if replace_sid:
                self._entries.pop(replace_sid, None)
            self._entries[sid] = entry
        return sid, entry

    async def get(self, sid: str | None, owner_uid: str) -> SessionLLMEntry | None:
        if not sid:
            return None
        async with self._lock:
            entry = self._entries.get(sid)
            if entry is None:
                return None
            if entry.expires_at <= self._clock():
                del self._entries[sid]
                return None
            if not secrets.compare_digest(entry.owner_uid, owner_uid):
                return None
            return entry

    async def delete(self, sid: str | None) -> None:
        if not sid:
            return
        async with self._lock:
            self._entries.pop(sid, None)

    async def purge_expired(self) -> int:
        now = self._clock()
        async with self._lock:
            expired = [sid for sid, e in self._entries.items() if e.expires_at <= now]
            for sid in expired:
                del self._entries[sid]
        return len(expired)

    def __len__(self) -> int:
        return len(self._entries)
