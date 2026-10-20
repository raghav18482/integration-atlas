"""Shared request dependencies: anonymous client identity, BYOK session, limits."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Request, Response

from app.errors import AppError
from app.security.session_manager import (
    LLM_COOKIE,
    UID_COOKIE,
    UID_MAX_AGE,
    SessionLLMEntry,
    new_opaque_id,
)
from app.services.llm.factory import EffectiveLLMConfig, default_config
from app.state import AppState


def get_state(request: Request) -> AppState:
    return request.app.state.atlas


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    return request.client.host if request.client else "unknown"


async def client_id(request: Request, response: Response, state: AppState = Depends(get_state)) -> str:
    """Anonymous, signed, server-minted browser identity (used for checklist ownership
    and to bind BYOK sessions). Unknown or tampered values are replaced, never adopted."""
    uid = state.signer.unsign_uid(request.cookies.get(UID_COOKIE))
    if uid is None:
        uid = new_opaque_id()
        response.set_cookie(
            UID_COOKIE,
            state.signer.sign_uid(uid),
            max_age=UID_MAX_AGE,
            httponly=True,
            secure=state.settings.cookie_secure,
            samesite="lax",
            path="/",
        )
    return uid


@dataclass
class LLMSessionContext:
    sid: str | None
    entry: SessionLLMEntry | None

    @property
    def cookie_present(self) -> bool:
        return self.sid is not None


async def llm_session(
    request: Request,
    uid: str = Depends(client_id),
    state: AppState = Depends(get_state),
) -> LLMSessionContext:
    sid = state.signer.unsign_session(request.cookies.get(LLM_COOKIE))
    entry = await state.sessions.get(sid, uid) if sid else None
    return LLMSessionContext(sid=sid, entry=entry)


def session_effective_config(ctx: LLMSessionContext) -> EffectiveLLMConfig | None:
    if ctx.entry is None:
        return None
    return EffectiveLLMConfig(
        provider_id=ctx.entry.provider_id,
        model=ctx.entry.model,
        source="session",
        api_key=ctx.entry.api_key,
    )


def require_effective_llm(ctx: LLMSessionContext, state: AppState) -> EffectiveLLMConfig:
    session_cfg = session_effective_config(ctx)
    if session_cfg is not None:
        return session_cfg
    if ctx.cookie_present:
        # The user chose their own key; do not silently switch to the paid default.
        raise AppError(
            "llm_session_expired",
            "Your personal API key session has expired. Re-enter your key, or switch to "
            "the app default in LLM settings.",
            status_code=409,
        )
    cfg = default_config(state.settings)
    if cfg is None:
        raise AppError(
            "llm_not_configured",
            "No language model is configured. Add your own API key in LLM settings "
            "(Anthropic, OpenAI, or OpenRouter), or set DEFAULT_LLM_PROVIDER, "
            "DEFAULT_LLM_MODEL and the matching API key on the server.",
            status_code=503,
        )
    return cfg


def enforce_limit(
    state: AppState, request: Request, uid: str, bucket: str, limit: int, window: float
) -> None:
    state.limiter.check(f"{bucket}:uid:{uid}", limit, window)
    state.limiter.check(f"{bucket}:ip:{client_ip(request)}", limit * 3, window)


def set_llm_cookie(response: Response, state: AppState, sid: str) -> None:
    response.set_cookie(
        LLM_COOKIE,
        state.signer.sign_session(sid),
        max_age=state.sessions.ttl_seconds,
        httponly=True,
        secure=state.settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_llm_cookie(response: Response, state: AppState) -> None:
    response.delete_cookie(
        LLM_COOKIE, path="/", httponly=True, secure=state.settings.cookie_secure, samesite="lax"
    )
