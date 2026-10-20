"""Persistence for guides, evidence, checklist progress, and feedback."""

from __future__ import annotations

import re
import secrets
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import ChecklistProgressRow, ClaimRow, FeedbackReportRow, GuideRow, SourceRow
from app.schemas.guide import IntegrationGuide


def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def provider_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:120] or "unknown"


def new_slug(provider_name: str) -> str:
    base = provider_key(provider_name)[:50].strip("-") or "app"
    return f"{base}-{secrets.token_hex(3)}"


def _content(guide: IntegrationGuide) -> dict:
    return guide.model_dump(mode="json", exclude={"sources", "claims"})


def _source_rows(guide: IntegrationGuide) -> list[SourceRow]:
    return [
        SourceRow(
            key=s.id,
            position=i,
            title=s.title,
            url=s.url,
            domain=s.domain,
            source_type=s.source_type.value,
            retrieval_status=s.retrieval_status.value,
            accessed_at=s.accessed_at,
            error=s.error,
            excerpt=s.excerpt,
        )
        for i, s in enumerate(guide.sources)
    ]


def _claim_rows(guide: IntegrationGuide) -> list[ClaimRow]:
    return [
        ClaimRow(
            key=c.id,
            position=i,
            statement=c.statement,
            category=c.category.value,
            status=c.status.value,
            impact=c.impact.value,
            source_keys=list(c.source_ids),
            evidence_quote=c.evidence_quote,
            test_detail=c.test_detail,
            note=c.note,
        )
        for i, c in enumerate(guide.claims)
    ]


def _apply_columns(row: GuideRow, guide: IntegrationGuide) -> None:
    row.slug = guide.slug
    row.provider_name = guide.provider_name
    row.provider_key = provider_key(guide.provider_name)
    row.origin = guide.origin.value
    row.research_status = guide.research_status.value
    row.authentication_model = guide.authentication_model.value
    row.integration_context = guide.integration_context.value
    row.intended_use_case = guide.intended_use_case
    row.submitted_input = guide.submitted_input
    row.seed_parent_slug = guide.seed_parent_slug
    row.research_run_id = guide.research_run_id
    row.generated_at = guide.generated_at
    row.last_checked_at = guide.last_checked_at
    row.content = _content(guide)


def row_to_guide(row: GuideRow) -> IntegrationGuide:
    data = dict(row.content)
    data["sources"] = [
        {
            "id": s.key,
            "title": s.title,
            "url": s.url,
            "domain": s.domain,
            "source_type": s.source_type,
            "retrieval_status": s.retrieval_status,
            "accessed_at": as_utc(s.accessed_at),
            "error": s.error,
            "excerpt": s.excerpt,
        }
        for s in row.sources
    ]
    data["claims"] = [
        {
            "id": c.key,
            "statement": c.statement,
            "category": c.category,
            "status": c.status,
            "source_ids": list(c.source_keys or []),
            "evidence_quote": c.evidence_quote,
            "impact": c.impact,
            "test_detail": c.test_detail,
            "note": c.note,
        }
        for c in row.claims
    ]
    return IntegrationGuide.model_validate(data)


async def get_guide_row(session: AsyncSession, slug: str) -> GuideRow | None:
    result = await session.execute(
        select(GuideRow)
        .where(GuideRow.slug == slug)
        .options(selectinload(GuideRow.sources), selectinload(GuideRow.claims))
    )
    return result.scalar_one_or_none()


async def save_guide(session: AsyncSession, guide: IntegrationGuide) -> GuideRow:
    """Insert, or replace in place when a guide with this slug exists (keeps id and progress)."""
    row = await get_guide_row(session, guide.slug)
    if row is None:
        row = GuideRow(id=guide.id)
        session.add(row)
    else:
        # Delete old evidence rows before inserting new ones with the same keys
        # (the unit of work would otherwise insert first and hit the unique constraint).
        row.sources.clear()
        row.claims.clear()
        await session.flush()
    _apply_columns(row, guide)
    row.sources = _source_rows(guide)
    row.claims = _claim_rows(guide)
    await session.commit()
    return row


async def list_guides(
    session: AsyncSession,
    *,
    q: str | None,
    origin: str | None,
    context: str | None,
    limit: int,
    offset: int,
) -> tuple[list[GuideRow], int]:
    stmt = select(GuideRow)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(GuideRow.provider_name).like(like),
                func.lower(GuideRow.intended_use_case).like(like),
                func.lower(GuideRow.submitted_input).like(like),
            )
        )
    if origin:
        stmt = stmt.where(GuideRow.origin == origin)
    if context:
        stmt = stmt.where(GuideRow.integration_context == context)
    total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (
        (
            await session.execute(
                stmt.order_by(GuideRow.origin.desc(), GuideRow.last_checked_at.desc())
                .limit(limit)
                .offset(offset)
            )
        )
        .scalars()
        .all()
    )
    return list(rows), int(total)


async def get_progress(session: AsyncSession, guide_id: str, owner_uid: str) -> dict[str, bool]:
    rows = (
        (
            await session.execute(
                select(ChecklistProgressRow).where(
                    ChecklistProgressRow.guide_id == guide_id, ChecklistProgressRow.owner_uid == owner_uid
                )
            )
        )
        .scalars()
        .all()
    )
    return {r.item_id: r.completed for r in rows}


async def set_progress(
    session: AsyncSession, guide_id: str, owner_uid: str, item_id: str, completed: bool
) -> None:
    row = (
        await session.execute(
            select(ChecklistProgressRow).where(
                ChecklistProgressRow.guide_id == guide_id,
                ChecklistProgressRow.owner_uid == owner_uid,
                ChecklistProgressRow.item_id == item_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        session.add(
            ChecklistProgressRow(guide_id=guide_id, owner_uid=owner_uid, item_id=item_id, completed=completed)
        )
    else:
        row.completed = completed
    await session.commit()


async def add_feedback(
    session: AsyncSession, guide_id: str, owner_uid: str, target_id: str | None, message: str
) -> None:
    session.add(
        FeedbackReportRow(guide_id=guide_id, owner_uid=owner_uid, target_id=target_id, message=message)
    )
    await session.commit()
