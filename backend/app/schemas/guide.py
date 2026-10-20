"""The IntegrationGuide data model.

Design rules enforced here (not just in prompts):
- Every claim's source IDs must exist; every referenced claim ID must exist.
- `tested` claims must describe the test that was actually performed.
- `officially_documented` / `cross_checked` claims need a retrieved source.
- Approval and waiting-time conclusions must be backed by supported claims
  (enforced in services.guide_generator.apply_evidence_rules).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AuthenticationModel(StrEnum):
    OAUTH2 = "oauth2"
    OAUTH1 = "oauth1"
    API_KEY = "api_key"
    OTHER = "other"
    UNKNOWN = "unknown"


class IntegrationContext(StrEnum):
    PERSONAL = "personal"
    INTERNAL = "internal"
    MULTI_TENANT_SAAS = "multi_tenant_saas"


class ClaimStatus(StrEnum):
    TESTED = "tested"
    CROSS_CHECKED = "cross_checked"
    OFFICIALLY_DOCUMENTED = "officially_documented"
    INFERRED = "inferred"
    ESTIMATED = "estimated"
    UNKNOWN = "unknown"


# Statuses that count as evidence (vs. model judgment).
SUPPORTED_STATUSES = frozenset(
    {ClaimStatus.TESTED, ClaimStatus.CROSS_CHECKED, ClaimStatus.OFFICIALLY_DOCUMENTED}
)

# Weakest-first ordering used to derive a step's status from its claims.
STATUS_STRENGTH = {
    ClaimStatus.UNKNOWN: 0,
    ClaimStatus.ESTIMATED: 1,
    ClaimStatus.INFERRED: 2,
    ClaimStatus.OFFICIALLY_DOCUMENTED: 3,
    ClaimStatus.CROSS_CHECKED: 4,
    ClaimStatus.TESTED: 5,
}


class ClaimCategory(StrEnum):
    AUTH_MODEL = "auth_model"
    REGISTRATION = "registration"
    CREDENTIALS = "credentials"
    REDIRECT_URI = "redirect_uri"
    SCOPES = "scopes"
    CONSENT = "consent"
    VERIFICATION = "verification"
    DISTRIBUTION = "distribution"
    REVIEW_TIMELINE = "review_timeline"
    ACCESS_REQUIREMENTS = "access_requirements"
    RATE_LIMITS = "rate_limits"
    ENDPOINTS = "endpoints"
    TESTING = "testing"
    OTHER = "other"


class Impact(StrEnum):
    HIGH = "high"
    NORMAL = "normal"


class ApprovalStatus(StrEnum):
    REQUIRED = "required"
    NOT_REQUIRED = "not_required"
    CONDITIONAL = "conditional"
    UNCLEAR = "unclear"


class ApprovalKind(StrEnum):
    APP_REGISTRATION = "app_registration"
    USER_CONSENT = "user_consent"
    ADMIN_CONSENT = "admin_consent"
    PROVIDER_VERIFICATION = "provider_verification"
    MARKETPLACE_LISTING = "marketplace_listing"
    PRODUCTION_ACCESS = "production_access"


class ExternalWaitKind(StrEnum):
    NONE = "none"
    KNOWN = "known"
    ESTIMATED = "estimated"
    UNKNOWN = "unknown"


class Responsible(StrEnum):
    AGENT = "agent"
    DEVELOPER = "developer"
    DEVELOPER_WITH_AGENT = "developer_with_agent"
    PROVIDER = "provider"
    WORKSPACE_ADMIN = "workspace_admin"
    END_USER = "end_user"


class StepPhase(StrEnum):
    PREREQUISITES = "prerequisites"
    REGISTRATION = "registration"
    CREDENTIALS = "credentials"
    SCOPES = "scopes"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    VERIFICATION = "verification"
    DISTRIBUTION = "distribution"
    LAUNCH = "launch"


class SourceType(StrEnum):
    OFFICIAL_DOCS = "official_docs"
    OFFICIAL_API_REFERENCE = "official_api_reference"
    OFFICIAL_POLICY = "official_policy"
    OFFICIAL_SUPPORT = "official_support"
    PROVIDER_METADATA = "provider_metadata"
    SECONDARY = "secondary"


OFFICIAL_SOURCE_TYPES = frozenset(set(SourceType) - {SourceType.SECONDARY})


class RetrievalStatus(StrEnum):
    RETRIEVED = "retrieved"
    SNIPPET_ONLY = "snippet_only"
    FAILED = "failed"
    BLOCKED = "blocked"
    NOT_ATTEMPTED = "not_attempted"


class GuideOrigin(StrEnum):
    SEED = "seed"
    LIVE_RESEARCH = "live_research"


class GuideResearchStatus(StrEnum):
    SEED_CURATED = "seed_curated"
    COMPLETE = "complete"
    PARTIAL = "partial"


class PathKind(StrEnum):
    MANAGED_OAUTH = "managed_oauth"
    CUSTOM_OAUTH_APP = "custom_oauth_app"
    API_KEY = "api_key"
    OTHER = "other"


class ScopeSensitivity(StrEnum):
    BASIC = "basic"
    SENSITIVE = "sensitive"
    RESTRICTED = "restricted"
    ADMIN = "admin"
    UNKNOWN = "unknown"


class BlockerKind(StrEnum):
    BLOCKER = "blocker"
    RISK = "risk"
    UNKNOWN = "unknown"


SourceId = Annotated[str, Field(pattern=r"^S\d{1,3}$")]
ClaimId = Annotated[str, Field(pattern=r"^C\d{1,3}$")]
ItemId = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9\-]{0,63}$")]


class _Model(BaseModel):
    # Unknown keys are ignored so slightly-off LLM output does not burn a retry;
    # seed files are checked for unknown keys in tests instead.
    model_config = ConfigDict(extra="ignore", use_enum_values=False)


# ---------------------------------------------------------------- evidence


class Source(_Model):
    id: SourceId
    title: str = Field(max_length=300)
    url: str = Field(max_length=2048, pattern=r"^https?://")
    domain: str = Field(max_length=253)
    source_type: SourceType
    accessed_at: datetime | None = None
    retrieval_status: RetrievalStatus
    error: str | None = Field(default=None, max_length=300)
    supported_claim_ids: list[ClaimId] = Field(default_factory=list)
    # Stored server-side for grounding Q&A; never serialized to API clients.
    excerpt: str | None = Field(default=None, exclude=True)


class Claim(_Model):
    id: ClaimId
    statement: str = Field(min_length=3, max_length=1000)
    category: ClaimCategory
    status: ClaimStatus
    source_ids: list[SourceId] = Field(default_factory=list)
    evidence_quote: str | None = Field(default=None, max_length=1200)
    impact: Impact = Impact.NORMAL
    test_detail: str | None = Field(default=None, max_length=600)
    note: str | None = Field(default=None, max_length=600)


class VerificationReport(_Model):
    checked_at: datetime
    method: str
    sources_total: int = 0
    sources_retrieved: int = 0
    sources_snippet_only: int = 0
    sources_failed: int = 0
    claims_total: int = 0
    claims_by_status: dict[str, int] = Field(default_factory=dict)
    evidence_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    quote_mismatch_claim_ids: list[ClaimId] = Field(default_factory=list)
    unsupported_claim_ids: list[ClaimId] = Field(default_factory=list)
    coercions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------- guide body


class ExternalWait(_Model):
    kind: ExternalWaitKind
    summary: str = Field(max_length=400)
    range_text: str | None = Field(default=None, max_length=120)
    explanation: str = Field(default="", max_length=800)
    claim_ids: list[ClaimId] = Field(default_factory=list)


class EffortEstimate(_Model):
    low_hours: float = Field(ge=0, le=500)
    high_hours: float = Field(ge=0, le=500)
    basis: str = Field(max_length=600)
    status: Literal[ClaimStatus.ESTIMATED] = ClaimStatus.ESTIMATED

    @model_validator(mode="after")
    def _ordered(self) -> EffortEstimate:
        if self.low_hours > self.high_hours:
            raise ValueError("effort_estimate.low_hours must be <= high_hours")
        return self


class PathOption(_Model):
    kind: PathKind
    title: str = Field(max_length=120)
    summary: str = Field(max_length=600)
    when_to_choose: str = Field(default="", max_length=400)
    tradeoffs: list[str] = Field(default_factory=list, max_length=8)
    recommended: bool = False
    claim_ids: list[ClaimId] = Field(default_factory=list)


class RecommendedPath(_Model):
    summary: str = Field(max_length=800)
    options: list[PathOption] = Field(default_factory=list, max_length=4)


class Prerequisite(_Model):
    title: str = Field(max_length=160)
    detail: str = Field(max_length=600)
    claim_ids: list[ClaimId] = Field(default_factory=list)


class SetupStep(_Model):
    id: ItemId
    phase: StepPhase
    title: str = Field(max_length=160)
    explanation: str = Field(max_length=1500)
    why_it_matters: str = Field(max_length=600)
    expected_outcome: str = Field(max_length=400)
    responsible: Responsible
    active_effort_minutes: int | None = Field(default=None, ge=0, le=2400)
    depends_on: list[ItemId] = Field(default_factory=list)
    claim_ids: list[ClaimId] = Field(default_factory=list)
    verification_status: ClaimStatus = ClaimStatus.INFERRED


class ScopePermission(_Model):
    name: str = Field(max_length=200)
    description: str = Field(max_length=500)
    sensitivity: ScopeSensitivity = ScopeSensitivity.UNKNOWN
    needed_for: str = Field(default="", max_length=300)
    claim_ids: list[ClaimId] = Field(default_factory=list)


class ApprovalItem(_Model):
    kind: ApprovalKind
    status: ApprovalStatus
    title: str = Field(max_length=160)
    applies_when: str = Field(default="", max_length=400)
    description: str = Field(max_length=900)
    external_wait: ExternalWait | None = None
    claim_ids: list[ClaimId] = Field(default_factory=list)


class TestingStep(_Model):
    title: str = Field(max_length=160)
    detail: str = Field(max_length=700)
    claim_ids: list[ClaimId] = Field(default_factory=list)


class BlockerOrUnknown(_Model):
    id: ItemId
    kind: BlockerKind
    title: str = Field(max_length=200)
    detail: str = Field(max_length=900)
    mitigation: str = Field(default="", max_length=600)
    claim_ids: list[ClaimId] = Field(default_factory=list)


class AgentDeveloperAction(_Model):
    action: str = Field(max_length=300)
    actor: Literal["agent", "developer", "both"]
    rationale: str = Field(default="", max_length=400)


class ChecklistItem(_Model):
    id: ItemId
    label: str = Field(max_length=200)
    step_id: ItemId | None = None
    responsible: Responsible = Responsible.DEVELOPER


class GuideBody(_Model):
    """Everything that describes the integration work (LLM-draftable)."""

    authentication_model: AuthenticationModel
    auth_model_claim_ids: list[ClaimId] = Field(default_factory=list)
    overview: str = Field(max_length=2000)
    recommended_path: RecommendedPath
    effort_estimate: EffortEstimate
    external_wait: ExternalWait
    approval_status: ApprovalStatus
    approval_summary: str = Field(max_length=900)
    approval_claim_ids: list[ClaimId] = Field(default_factory=list)
    prerequisites: list[Prerequisite] = Field(default_factory=list, max_length=12)
    setup_steps: list[SetupStep] = Field(min_length=1, max_length=30)
    scopes_or_permissions: list[ScopePermission] = Field(default_factory=list, max_length=40)
    approval_and_distribution: list[ApprovalItem] = Field(default_factory=list, max_length=12)
    testing_plan: list[TestingStep] = Field(default_factory=list, max_length=12)
    blockers_and_unknowns: list[BlockerOrUnknown] = Field(default_factory=list, max_length=20)
    agent_vs_developer_actions: list[AgentDeveloperAction] = Field(default_factory=list, max_length=20)
    context_variations: dict[IntegrationContext, str] = Field(default_factory=dict)

    def referenced_claim_ids(self) -> set[str]:
        refs: set[str] = set(self.auth_model_claim_ids) | set(self.approval_claim_ids)
        refs |= set(self.external_wait.claim_ids)
        for opt in self.recommended_path.options:
            refs |= set(opt.claim_ids)
        for group in (
            self.prerequisites,
            self.setup_steps,
            self.scopes_or_permissions,
            self.approval_and_distribution,
            self.testing_plan,
            self.blockers_and_unknowns,
        ):
            for item in group:
                refs |= set(item.claim_ids)
        for approval in self.approval_and_distribution:
            if approval.external_wait:
                refs |= set(approval.external_wait.claim_ids)
        return refs

    def body_reference_errors(self, claim_ids: set[str]) -> list[str]:
        errors: list[str] = []
        missing = sorted(self.referenced_claim_ids() - claim_ids)
        if missing:
            errors.append(f"References unknown claim IDs: {', '.join(missing)}")
        step_ids = [s.id for s in self.setup_steps]
        if len(step_ids) != len(set(step_ids)):
            errors.append("setup_steps contain duplicate ids")
        for step in self.setup_steps:
            bad = [d for d in step.depends_on if d not in step_ids or d == step.id]
            if bad:
                errors.append(f"Step {step.id} depends on unknown steps: {', '.join(bad)}")
        blocker_ids = [b.id for b in self.blockers_and_unknowns]
        if len(blocker_ids) != len(set(blocker_ids)):
            errors.append("blockers_and_unknowns contain duplicate ids")
        return errors


class GuideDraft(GuideBody):
    """What the generation LLM must return. Evidence and metadata are attached server-side."""


class IntegrationGuide(GuideBody):
    id: str = Field(max_length=64)
    slug: ItemId
    provider_name: str = Field(max_length=120)
    provider_domains: list[str] = Field(default_factory=list, max_length=10)
    submitted_input: str = Field(max_length=2048)
    submitted_url: str | None = Field(default=None, max_length=2048)
    intended_use_case: str = Field(default="", max_length=1000)
    integration_context: IntegrationContext
    additional_context: str = Field(default="", max_length=2000)
    origin: GuideOrigin
    research_status: GuideResearchStatus
    generated_at: datetime
    last_checked_at: datetime
    seed_parent_slug: str | None = None
    research_run_id: str | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    sources: list[Source] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    checklist_state: list[ChecklistItem] = Field(default_factory=list)
    verification_report: VerificationReport

    @model_validator(mode="after")
    def _integrity(self) -> IntegrationGuide:
        source_ids = [s.id for s in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("Duplicate source IDs")
        claim_ids = [c.id for c in self.claims]
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("Duplicate claim IDs")

        sources_by_id = {s.id: s for s in self.sources}
        for claim in self.claims:
            unknown = [sid for sid in claim.source_ids if sid not in sources_by_id]
            if unknown:
                raise ValueError(f"Claim {claim.id} references unknown sources: {unknown}")
            if claim.status == ClaimStatus.TESTED and not claim.test_detail:
                raise ValueError(f"Claim {claim.id} is marked tested without test_detail")
            if claim.status in (ClaimStatus.OFFICIALLY_DOCUMENTED, ClaimStatus.CROSS_CHECKED):
                retrieved = [
                    sid
                    for sid in claim.source_ids
                    if sources_by_id[sid].retrieval_status == RetrievalStatus.RETRIEVED
                ]
                if not retrieved:
                    raise ValueError(
                        f"Claim {claim.id} is marked {claim.status.value} without a retrieved source"
                    )
                if claim.status == ClaimStatus.CROSS_CHECKED and len(set(retrieved)) < 2:
                    raise ValueError(f"Claim {claim.id} is cross_checked with fewer than 2 sources")

        errors = self.body_reference_errors(set(claim_ids))
        if errors:
            raise ValueError("; ".join(errors))

        step_ids = {s.id for s in self.setup_steps}
        item_ids = [i.id for i in self.checklist_state]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("Duplicate checklist item IDs")
        for item in self.checklist_state:
            if item.step_id and item.step_id not in step_ids:
                raise ValueError(f"Checklist item {item.id} references unknown step {item.step_id}")

        # supported_claim_ids is derived data: always recompute it from claims.
        for source in self.sources:
            source.supported_claim_ids = [c.id for c in self.claims if source.id in c.source_ids]
        return self
