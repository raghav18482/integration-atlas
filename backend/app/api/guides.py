from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query, Request

from app.api.deps import (
    LLMSessionContext,
    client_id,
    enforce_limit,
    get_state,
    llm_session,
    require_effective_llm,
)
from app.api.research import check_research_limits, start_run
from app.db import repository
from app.db.repository import as_utc
from app.errors import AppError
from app.schemas.api import (
    ChatRequest,
    ChatResponse,
    ChecklistProgress,
    ChecklistUpdate,
    FeedbackAccepted,
    FeedbackRequest,
    GuideList,
    GuideResponse,
    GuideSummary,
    LLMUsed,
    ResearchStarted,
)
from app.schemas.guide import GuideOrigin, IntegrationContext, IntegrationGuide
from app.services.chat_service import answer_question
from app.state import AppState

router = APIRouter(prefix="/api/guides", tags=["guides"])

SLUG = Path(pattern=r"^[a-z0-9][a-z0-9\-]{0,79}$")


async def _load(state: AppState, slug: str) -> tuple[str, IntegrationGuide]:
    async with state.db.session() as session:
        row = await repository.get_guide_row(session, slug)
        if row is None:
            raise AppError("not_found", "Guide not found.", 404)
        return row.id, repository.row_to_guide(row)


def _progress(guide: IntegrationGuide, items: dict[str, bool]) -> ChecklistProgress:
    valid = {i.id for i in guide.checklist_state}
    filtered = {k: v for k, v in items.items() if k in valid}
    return ChecklistProgress(items=filtered, completed=sum(filtered.values()), total=len(valid))


@router.get("", response_model=GuideList)
async def list_guides(
    q: str | None = Query(default=None, max_length=100),
    origin: GuideOrigin | None = None,
    context: IntegrationContext | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    state: AppState = Depends(get_state),
) -> GuideList:
    async with state.db.session() as session:
        rows, total = await repository.list_guides(
            session,
            q=q.strip() if q else None,
            origin=origin.value if origin else None,
            context=context.value if context else None,
            limit=limit,
            offset=offset,
        )
    items = []
    for row in rows:
        report = (row.content or {}).get("verification_report", {})
        items.append(
            GuideSummary(
                slug=row.slug,
                provider_name=row.provider_name,
                authentication_model=row.authentication_model,
                intended_use_case=row.intended_use_case,
                integration_context=row.integration_context,
                origin=row.origin,
                research_status=row.research_status,
                generated_at=as_utc(row.generated_at),  # type: ignore[arg-type]
                last_checked_at=as_utc(row.last_checked_at),  # type: ignore[arg-type]
                evidence_coverage=float(report.get("evidence_coverage", 0.0)),
                claims_total=int(report.get("claims_total", 0)),
                sources_total=int(report.get("sources_total", 0)),
                approval_status=(row.content or {}).get("approval_status"),
                seed_parent_slug=row.seed_parent_slug,
            )
        )
    return GuideList(items=items, total=total, limit=limit, offset=offset)


@router.get("/{slug}", response_model=GuideResponse)
async def get_guide(
    slug: str = SLUG, uid: str = Depends(client_id), state: AppState = Depends(get_state)
) -> GuideResponse:
    guide_id, guide = await _load(state, slug)
    async with state.db.session() as session:
        items = await repository.get_progress(session, guide_id, uid)
    return GuideResponse(guide=guide, checklist_progress=_progress(guide, items))


@router.patch("/{slug}/checklist", response_model=ChecklistProgress)
async def update_checklist(
    body: ChecklistUpdate,
    slug: str = SLUG,
    uid: str = Depends(client_id),
    state: AppState = Depends(get_state),
) -> ChecklistProgress:
    guide_id, guide = await _load(state, slug)
    if body.item_id not in {i.id for i in guide.checklist_state}:
        raise AppError("unknown_checklist_item", "That checklist item does not exist in this guide.", 422)
    async with state.db.session() as session:
        await repository.set_progress(session, guide_id, uid, body.item_id, body.completed)
        items = await repository.get_progress(session, guide_id, uid)
    return _progress(guide, items)


@router.post("/{slug}/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    request: Request,
    slug: str = SLUG,
    uid: str = Depends(client_id),
    ctx: LLMSessionContext = Depends(llm_session),
    state: AppState = Depends(get_state),
) -> ChatResponse:
    _, guide = await _load(state, slug)
    cfg = require_effective_llm(ctx, state)
    enforce_limit(state, request, uid, "chat", state.settings.rate_limit_chat_per_hour, 3600)
    answer = await answer_question(cfg.build(), guide, body.question.strip(), body.history)
    return ChatResponse(
        **answer.model_dump(),
        llm=LLMUsed(provider=cfg.provider_id, model=cfg.model, source=cfg.source),
    )


@router.post("/{slug}/refresh", status_code=202, response_model=ResearchStarted)
async def refresh(
    request: Request,
    slug: str = SLUG,
    uid: str = Depends(client_id),
    ctx: LLMSessionContext = Depends(llm_session),
    state: AppState = Depends(get_state),
) -> ResearchStarted:
    _, guide = await _load(state, slug)
    cfg = require_effective_llm(ctx, state)
    check_research_limits(state, request, uid, cfg)
    return await start_run(
        state,
        cfg,
        query=guide.provider_name if guide.origin == GuideOrigin.SEED else guide.submitted_input,
        intended_use_case=guide.intended_use_case,
        integration_context=guide.integration_context,
        additional_context=guide.additional_context,
        refresh_of_slug=guide.slug,
        submitted_url=guide.submitted_url,
    )


@router.post("/{slug}/reports", status_code=201, response_model=FeedbackAccepted)
async def report_issue(
    body: FeedbackRequest,
    request: Request,
    slug: str = SLUG,
    uid: str = Depends(client_id),
    state: AppState = Depends(get_state),
) -> FeedbackAccepted:
    guide_id, _ = await _load(state, slug)
    enforce_limit(state, request, uid, "reports", 10, 3600)
    async with state.db.session() as session:
        await repository.add_feedback(session, guide_id, uid, body.target_id, body.message.strip())
    return FeedbackAccepted()
