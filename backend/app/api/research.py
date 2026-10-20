from __future__ import annotations

import re

from fastapi import APIRouter, Depends, Path, Request

from app.api.deps import (
    LLMSessionContext,
    client_id,
    enforce_limit,
    get_state,
    llm_session,
    require_effective_llm,
)
from app.db.models import ResearchRunRow
from app.db.repository import as_utc
from app.errors import AppError
from app.schemas.api import (
    LLMUsed,
    ResearchEvent,
    ResearchRequest,
    ResearchRunOut,
    ResearchSourceEntry,
    ResearchStarted,
    StageInfo,
)
from app.schemas.guide import IntegrationContext
from app.security.url_validation import UnsafeURLError, validate_public_url
from app.services.llm.factory import EffectiveLLMConfig
from app.services.research_runner import create_run, launch, new_run_id
from app.services.research_workflow import STAGES, ResearchInput
from app.state import AppState

router = APIRouter(prefix="/api", tags=["research"])

_DOMAIN_LIKE = re.compile(r"^[a-z0-9][a-z0-9.\-]*\.[a-z]{2,}(/\S*)?$", re.IGNORECASE)
RUN_ID = Path(pattern=r"^[0-9a-f\-]{36}$")


def interpret_query(raw: str) -> tuple[str, str | None]:
    text = raw.strip()
    if re.match(r"^[a-z][a-z0-9+.\-]*://", text, re.IGNORECASE):
        return text, text
    if " " not in text and _DOMAIN_LIKE.match(text):
        return text, f"https://{text}"
    return text, None


def check_research_limits(state: AppState, request: Request, uid: str, cfg: EffectiveLLMConfig) -> None:
    s = state.settings
    if cfg.source == "session":
        enforce_limit(state, request, uid, "research-byok", s.rate_limit_research_byok_per_hour, 3600)
    else:
        enforce_limit(state, request, uid, "research-default", s.rate_limit_research_default_per_hour, 3600)
        # Global ceiling on spend against the operator's key.
        state.limiter.check("research-default:global", s.rate_limit_research_default_per_hour * 10, 3600)


async def start_run(
    state: AppState,
    cfg: EffectiveLLMConfig,
    *,
    query: str,
    intended_use_case: str,
    integration_context: IntegrationContext,
    additional_context: str,
    refresh_of_slug: str | None = None,
    submitted_url: str | None = None,
) -> ResearchStarted:
    text, url = interpret_query(query)
    url = submitted_url or url
    if url:
        try:
            url = (await validate_public_url(url)).url
        except UnsafeURLError as exc:
            raise AppError("unsafe_url", f"That URL cannot be researched: {exc}", 400) from None
    if not url and not state.settings.search_configured:
        raise AppError(
            "search_not_configured",
            "Web search is not configured on this server, so research needs a starting URL. "
            "Enter the provider's official developer documentation URL instead "
            "(for example https://developers.example.com/docs/oauth).",
            503,
        )
    inp = ResearchInput(
        run_id=new_run_id(),
        query=text,
        submitted_url=url,
        intended_use_case=intended_use_case.strip(),
        integration_context=integration_context,
        additional_context=additional_context.strip(),
        refresh_of_slug=refresh_of_slug,
    )
    await create_run(state, inp, cfg)
    launch(state, inp, cfg)
    return ResearchStarted(run_id=inp.run_id, status="queued")


def run_to_out(row: ResearchRunRow) -> ResearchRunOut:
    return ResearchRunOut(
        id=row.id,
        status=row.status,  # type: ignore[arg-type]
        stage=row.stage,
        stages=[StageInfo(key=k, label=v) for k, v in STAGES],
        query=row.input_text,
        submitted_url=row.submitted_url,
        intended_use_case=row.intended_use_case,
        integration_context=IntegrationContext(row.integration_context),
        provider_name=row.provider_name,
        refresh_of_slug=row.refresh_of_slug,
        events=[ResearchEvent.model_validate(e) for e in (row.events or [])],
        sources=[ResearchSourceEntry.model_validate(s) for s in (row.sources or [])],
        guide_slug=row.guide_slug,
        error_code=row.error_code,
        error_message=row.error_message,
        llm=LLMUsed(provider=row.llm_provider, model=row.llm_model, source=row.llm_source),
        created_at=as_utc(row.created_at),  # type: ignore[arg-type]
        finished_at=as_utc(row.finished_at),
    )


@router.post("/research", status_code=202, response_model=ResearchStarted)
async def start_research(
    body: ResearchRequest,
    request: Request,
    uid: str = Depends(client_id),
    ctx: LLMSessionContext = Depends(llm_session),
    state: AppState = Depends(get_state),
) -> ResearchStarted:
    cfg = require_effective_llm(ctx, state)
    check_research_limits(state, request, uid, cfg)
    return await start_run(
        state,
        cfg,
        query=body.query,
        intended_use_case=body.intended_use_case,
        integration_context=body.integration_context,
        additional_context=body.additional_context,
    )


@router.get("/research/{run_id}", response_model=ResearchRunOut)
async def get_research(run_id: str = RUN_ID, state: AppState = Depends(get_state)) -> ResearchRunOut:
    async with state.db.session() as session:
        row = await session.get(ResearchRunRow, run_id)
    if row is None:
        raise AppError("not_found", "Research run not found.", 404)
    return run_to_out(row)


@router.post("/research/{run_id}/retry", status_code=202, response_model=ResearchStarted)
async def retry_research(
    request: Request,
    run_id: str = RUN_ID,
    uid: str = Depends(client_id),
    ctx: LLMSessionContext = Depends(llm_session),
    state: AppState = Depends(get_state),
) -> ResearchStarted:
    async with state.db.session() as session:
        row = await session.get(ResearchRunRow, run_id)
    if row is None:
        raise AppError("not_found", "Research run not found.", 404)
    cfg = require_effective_llm(ctx, state)
    check_research_limits(state, request, uid, cfg)
    return await start_run(
        state,
        cfg,
        query=row.input_text,
        intended_use_case=row.intended_use_case,
        integration_context=IntegrationContext(row.integration_context),
        additional_context=row.additional_context,
        refresh_of_slug=row.refresh_of_slug,
        submitted_url=row.submitted_url,
    )
