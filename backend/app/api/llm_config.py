"""Session-only bring-your-own-key configuration endpoints.

Responses only ever contain provider, model, source, and expiry. The key is held
in memory server-side (see security.session_manager) and never echoed back.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime

from fastapi import APIRouter, Body, Depends, Query, Request, Response

from app.api.deps import (
    LLMSessionContext,
    clear_llm_cookie,
    client_id,
    enforce_limit,
    get_state,
    llm_session,
    require_effective_llm,
    set_llm_cookie,
)
from app.errors import AppError
from app.schemas.llm_config import (
    DefaultLLMInfo,
    LLMConfigRequest,
    LLMConfigStatus,
    LLMConfigTestRequest,
    LLMTestResult,
    ModelsResponse,
    ProviderOption,
    ProvidersResponse,
)
from app.services.llm.base import PROVIDER_LABELS, LLMError, LLMProvider
from app.services.llm.factory import (
    PROVIDER_INFO,
    InvalidModelError,
    UnsupportedProviderError,
    create_provider,
    list_models,
    validate_model_id,
    validate_provider_id,
)
from app.state import AppState

router = APIRouter(prefix="/api", tags=["llm"])


def _default_info(state: AppState) -> DefaultLLMInfo:
    s = state.settings
    if s.default_llm_configured:
        return DefaultLLMInfo(available=True, provider=s.default_llm_provider, model=s.default_llm_model)
    return DefaultLLMInfo(available=False)


def _status(state: AppState, ctx: LLMSessionContext) -> LLMConfigStatus:
    default = _default_info(state)
    if ctx.entry is not None:
        return LLMConfigStatus(
            source="session",
            provider=ctx.entry.provider_id,
            provider_label=PROVIDER_LABELS[ctx.entry.provider_id],
            model=ctx.entry.model,
            verified=ctx.entry.verified,
            expires_at=datetime.fromtimestamp(ctx.entry.expires_at, tz=UTC),
            default=default,
        )
    if ctx.cookie_present:
        return LLMConfigStatus(source="expired", default=default)
    if default.available:
        return LLMConfigStatus(
            source="default",
            provider=default.provider,
            provider_label=PROVIDER_LABELS.get(default.provider or "", default.provider),
            model=default.model,
            default=default,
        )
    return LLMConfigStatus(source="none", default=default)


def _validate_selection(provider: str, model: str) -> None:
    try:
        validate_provider_id(provider)
        validate_model_id(model)
    except UnsupportedProviderError as exc:
        raise AppError("unsupported_provider", str(exc), 400) from None
    except InvalidModelError as exc:
        raise AppError("invalid_model", str(exc), 400) from None


async def _connection_test(provider: LLMProvider) -> int:
    start = time.perf_counter()
    await provider.generate_text(
        "You are a connectivity check for an API client.",
        "Reply with the single word OK.",
        max_tokens=256,
    )
    return int((time.perf_counter() - start) * 1000)


@router.get("/llm/providers", response_model=ProvidersResponse)
async def providers(state: AppState = Depends(get_state)) -> ProvidersResponse:
    return ProvidersResponse(
        providers=[
            ProviderOption(
                id=p.id,
                label=p.label,
                sdk=p.sdk,
                key_hint=p.key_hint,
                suggested_models=list(p.suggested_models),
            )
            for p in PROVIDER_INFO.values()
        ],
        default=_default_info(state),
        search_configured=state.settings.search_configured,
    )


@router.get("/llm/models", response_model=ModelsResponse)
async def models(
    request: Request,
    provider: str = Query(max_length=32),
    uid: str = Depends(client_id),
    ctx: LLMSessionContext = Depends(llm_session),
    state: AppState = Depends(get_state),
) -> ModelsResponse:
    try:
        validate_provider_id(provider)
    except UnsupportedProviderError as exc:
        raise AppError("unsupported_provider", str(exc), 400) from None
    enforce_limit(state, request, uid, "models", 20, 60)
    key: str | None = None
    if ctx.entry is not None and ctx.entry.provider_id == provider:
        key = ctx.entry.api_key.get_secret_value()
    elif provider == state.settings.default_llm_provider:
        secret = state.settings.provider_key(provider)  # type: ignore[arg-type]
        key = secret.get_secret_value() if secret else None
    if provider != "openrouter" and not key:
        return ModelsResponse(
            provider=provider, models=list(PROVIDER_INFO[provider].suggested_models), source="suggested"
        )
    return ModelsResponse(provider=provider, models=await list_models(provider, key), source="live")


@router.get("/session/llm-config", response_model=LLMConfigStatus)
async def get_config(
    ctx: LLMSessionContext = Depends(llm_session), state: AppState = Depends(get_state)
) -> LLMConfigStatus:
    return _status(state, ctx)


@router.post("/session/llm-config", response_model=LLMConfigStatus)
async def save_config(
    request: Request,
    response: Response,
    body: LLMConfigRequest,
    uid: str = Depends(client_id),
    ctx: LLMSessionContext = Depends(llm_session),
    state: AppState = Depends(get_state),
) -> LLMConfigStatus:
    enforce_limit(state, request, uid, "llm-config", state.settings.rate_limit_llm_config_per_minute, 60)
    _validate_selection(body.provider, body.model)
    if body.test:
        provider = create_provider(body.provider, body.model, body.api_key.get_secret_value())
        await _connection_test(provider)  # LLMError -> safe error response; nothing stored
    sid, entry = await state.sessions.create(
        owner_uid=uid,
        provider_id=body.provider,
        model=body.model,
        api_key=body.api_key,
        verified=body.test,
        replace_sid=ctx.sid,
    )
    set_llm_cookie(response, state, sid)
    return _status(state, LLMSessionContext(sid=sid, entry=entry))


@router.post("/session/llm-config/test", response_model=LLMTestResult)
async def test_config(
    request: Request,
    body: LLMConfigTestRequest | None = Body(default=None),
    uid: str = Depends(client_id),
    ctx: LLMSessionContext = Depends(llm_session),
    state: AppState = Depends(get_state),
) -> LLMTestResult:
    enforce_limit(state, request, uid, "llm-config", state.settings.rate_limit_llm_config_per_minute, 60)
    if body is not None and body.api_key is not None:
        if not body.provider or not body.model:
            raise AppError("validation_error", "provider and model are required with api_key.", 422)
        _validate_selection(body.provider, body.model)
        provider = create_provider(body.provider, body.model, body.api_key.get_secret_value())
        latency = await _connection_test(provider)
        return LLMTestResult(
            ok=True, provider=body.provider, model=body.model, source="submitted", latency_ms=latency
        )
    cfg = require_effective_llm(ctx, state)
    latency = await _connection_test(cfg.build())
    return LLMTestResult(
        ok=True, provider=cfg.provider_id, model=cfg.model, source=cfg.source, latency_ms=latency
    )


@router.delete("/session/llm-config", status_code=204)
async def delete_config(
    ctx: LLMSessionContext = Depends(llm_session), state: AppState = Depends(get_state)
) -> Response:
    await state.sessions.delete(ctx.sid)
    response = Response(status_code=204)
    clear_llm_cookie(response, state)
    return response


__all__ = ["router", "LLMError"]
