from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.guide import IntegrationContext, IntegrationGuide
from app.services.chat_service import ChatTurn


class ResearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=2, max_length=2048, description="App name or official documentation URL")
    intended_use_case: str = Field(default="", max_length=1000)
    integration_context: IntegrationContext = IntegrationContext.MULTI_TENANT_SAAS
    additional_context: str = Field(default="", max_length=2000)


class ResearchStarted(BaseModel):
    run_id: str
    status: str


class StageInfo(BaseModel):
    key: str
    label: str


class ResearchEvent(BaseModel):
    ts: datetime
    stage: str
    label: str
    status: str
    message: str
    data: dict[str, Any] | None = None


class ResearchSourceEntry(BaseModel):
    id: str | None = None
    url: str
    title: str
    domain: str
    official: bool
    status: str
    error: str | None = None


class LLMUsed(BaseModel):
    provider: str | None
    model: str | None
    source: str | None


class ResearchRunOut(BaseModel):
    id: str
    status: Literal["queued", "running", "completed", "partial", "failed"]
    stage: str | None
    stages: list[StageInfo]
    query: str
    submitted_url: str | None
    intended_use_case: str
    integration_context: IntegrationContext
    provider_name: str | None
    refresh_of_slug: str | None
    events: list[ResearchEvent]
    sources: list[ResearchSourceEntry]
    guide_slug: str | None
    error_code: str | None
    error_message: str | None
    llm: LLMUsed
    created_at: datetime
    finished_at: datetime | None


class GuideSummary(BaseModel):
    slug: str
    provider_name: str
    authentication_model: str
    intended_use_case: str
    integration_context: str
    origin: str
    research_status: str
    generated_at: datetime
    last_checked_at: datetime
    evidence_coverage: float
    claims_total: int
    sources_total: int
    approval_status: str | None = None
    seed_parent_slug: str | None = None


class GuideList(BaseModel):
    items: list[GuideSummary]
    total: int
    limit: int
    offset: int


class ChecklistProgress(BaseModel):
    items: dict[str, bool]
    completed: int
    total: int


class GuideResponse(BaseModel):
    guide: IntegrationGuide
    checklist_progress: ChecklistProgress


class ChecklistUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(pattern=r"^[a-z0-9][a-z0-9\-]{0,63}$")
    completed: bool


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=2, max_length=1000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=8)


class ChatResponse(BaseModel):
    answer: str
    cited_claim_ids: list[str]
    cited_source_ids: list[str]
    grounding: Literal["grounded", "partial", "insufficient"]
    needs_fresh_research: bool
    llm: LLMUsed


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: str | None = Field(default=None, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9\-]{0,63}$")
    message: str = Field(min_length=5, max_length=2000)


class FeedbackAccepted(BaseModel):
    ok: bool = True
