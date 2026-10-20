"""SQLAlchemy models. Session-only API keys are deliberately absent from every table."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class GuideRow(Base):
    __tablename__ = "guides"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    provider_name: Mapped[str] = mapped_column(String(120))
    provider_key: Mapped[str] = mapped_column(String(120), index=True)
    origin: Mapped[str] = mapped_column(String(20), index=True)
    research_status: Mapped[str] = mapped_column(String(20))
    authentication_model: Mapped[str] = mapped_column(String(20))
    integration_context: Mapped[str] = mapped_column(String(32))
    intended_use_case: Mapped[str] = mapped_column(Text, default="")
    submitted_input: Mapped[str] = mapped_column(String(2048))
    seed_parent_slug: Mapped[str | None] = mapped_column(String(80), nullable=True)
    research_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    # Guide body + metadata (everything except sources and claims).
    content: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    sources: Mapped[list[SourceRow]] = relationship(
        back_populates="guide", cascade="all, delete-orphan", order_by="SourceRow.position"
    )
    claims: Mapped[list[ClaimRow]] = relationship(
        back_populates="guide", cascade="all, delete-orphan", order_by="ClaimRow.position"
    )


class SourceRow(Base):
    __tablename__ = "sources"
    __table_args__ = (UniqueConstraint("guide_id", "key", name="uq_source_guide_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guide_id: Mapped[str] = mapped_column(ForeignKey("guides.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(8))
    position: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(300))
    url: Mapped[str] = mapped_column(String(2048))
    domain: Mapped[str] = mapped_column(String(253), index=True)
    source_type: Mapped[str] = mapped_column(String(32))
    retrieval_status: Mapped[str] = mapped_column(String(20))
    accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(String(300), nullable=True)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)

    guide: Mapped[GuideRow] = relationship(back_populates="sources")


class ClaimRow(Base):
    __tablename__ = "claims"
    __table_args__ = (UniqueConstraint("guide_id", "key", name="uq_claim_guide_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guide_id: Mapped[str] = mapped_column(ForeignKey("guides.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(8))
    position: Mapped[int] = mapped_column(Integer, default=0)
    statement: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), index=True)
    impact: Mapped[str] = mapped_column(String(10))
    source_keys: Mapped[list[str]] = mapped_column(JSON, default=list)
    evidence_quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    test_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    guide: Mapped[GuideRow] = relationship(back_populates="claims")


class ResearchRunRow(Base):
    __tablename__ = "research_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), index=True)  # queued|running|completed|partial|failed
    stage: Mapped[str | None] = mapped_column(String(40), nullable=True)
    input_text: Mapped[str] = mapped_column(String(2048))
    submitted_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    intended_use_case: Mapped[str] = mapped_column(Text, default="")
    integration_context: Mapped[str] = mapped_column(String(32))
    additional_context: Mapped[str] = mapped_column(Text, default="")
    refresh_of_slug: Mapped[str | None] = mapped_column(String(80), nullable=True)
    guide_slug: Mapped[str | None] = mapped_column(String(80), nullable=True)
    provider_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    events: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    sources: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Which model ran the research. Never the key.
    llm_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    llm_source: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ChecklistProgressRow(Base):
    __tablename__ = "checklist_progress"
    __table_args__ = (UniqueConstraint("guide_id", "owner_uid", "item_id", name="uq_progress_owner_item"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guide_id: Mapped[str] = mapped_column(ForeignKey("guides.id", ondelete="CASCADE"), index=True)
    owner_uid: Mapped[str] = mapped_column(String(64), index=True)
    item_id: Mapped[str] = mapped_column(String(64))
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class FeedbackReportRow(Base):
    __tablename__ = "feedback_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guide_id: Mapped[str] = mapped_column(ForeignKey("guides.id", ondelete="CASCADE"), index=True)
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    message: Mapped[str] = mapped_column(Text)
    owner_uid: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
