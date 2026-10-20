from __future__ import annotations

import json
import types
import typing

import pytest
from pydantic import BaseModel, ValidationError

from app.schemas.guide import (
    ApprovalStatus,
    ClaimStatus,
    ExternalWaitKind,
    GuideBody,
    IntegrationGuide,
)
from app.seed.loader import SEED_DIR, build_seed, load_seed_guides
from app.services.guide_generator import apply_evidence_rules


def _seed_raw(name: str) -> dict:
    return json.loads((SEED_DIR / f"{name}.json").read_text())


def _guide(name: str = "slack") -> IntegrationGuide:
    return build_seed(_seed_raw(name))


def test_seed_guides_load_and_differ():
    guides = {g.slug: g for g in load_seed_guides()}
    assert set(guides) == {"slack", "github", "google"}
    assert guides["google"].approval_status == ApprovalStatus.REQUIRED
    assert guides["slack"].approval_status == ApprovalStatus.CONDITIONAL
    assert guides["github"].external_wait.kind == ExternalWaitKind.UNKNOWN
    for g in guides.values():
        assert g.origin.value == "seed"
        assert g.checklist_state, "checklist derived from steps"
        assert g.verification_report.claims_total == len(g.claims)


def _unknown_keys(model: type[BaseModel], data: object, path: str = "") -> list[str]:
    problems: list[str] = []
    if not isinstance(data, dict):
        return problems
    for key, value in data.items():
        if key not in model.model_fields:
            problems.append(f"{path}{key}")
            continue
        annotation = model.model_fields[key].annotation
        for candidate in (annotation, *typing.get_args(annotation)):
            inner = (
                typing.get_args(candidate)
                if typing.get_origin(candidate) in (list, types.UnionType)
                else (candidate,)
            )
            for cls in inner:
                if isinstance(cls, type) and issubclass(cls, BaseModel):
                    items = value if isinstance(value, list) else [value]
                    for i, item in enumerate(items):
                        problems += _unknown_keys(cls, item, f"{path}{key}[{i}].")
    return problems


@pytest.mark.parametrize("name", ["slack", "github", "google"])
def test_seed_files_have_no_unknown_fields(name):
    assert _unknown_keys(IntegrationGuide, _seed_raw(name)) == []


def test_tested_claims_only_where_a_test_was_recorded():
    for g in load_seed_guides():
        for c in g.claims:
            if c.status == ClaimStatus.TESTED:
                assert (
                    c.test_detail
                    and "Fetched" in c.test_detail
                    or "discovery document" in (c.test_detail or "")
                )


def test_invalid_source_reference_rejected():
    raw = _seed_raw("slack")
    raw["claims"][0]["source_ids"] = ["S99"]
    with pytest.raises(ValidationError, match="unknown sources"):
        build_seed(raw)


def test_unknown_claim_reference_in_step_rejected():
    raw = _seed_raw("github")
    raw["setup_steps"][0]["claim_ids"] = ["C999"]
    with pytest.raises(ValidationError, match="unknown claim"):
        build_seed(raw)


def test_tested_without_detail_rejected():
    raw = _seed_raw("google")
    for c in raw["claims"]:
        if c["status"] == "tested":
            c.pop("test_detail")
            break
    with pytest.raises(ValidationError, match="tested without test_detail"):
        build_seed(raw)


def test_documented_claim_needs_retrieved_source():
    raw = _seed_raw("slack")
    raw["sources"][0]["retrieval_status"] = "failed"
    with pytest.raises(ValidationError, match="without a retrieved source"):
        build_seed(raw)


def test_cross_checked_needs_two_sources():
    raw = _seed_raw("slack")
    claim = next(c for c in raw["claims"] if c["status"] == "cross_checked")
    claim["source_ids"] = claim["source_ids"][:1]
    with pytest.raises(ValidationError, match="fewer than 2"):
        build_seed(raw)


def test_evidence_rules_coerce_unsupported_conclusions():
    guide = _guide("slack")
    body = GuideBody.model_validate(guide.model_dump(include=set(GuideBody.model_fields)))
    unknown_claim = next(c for c in guide.claims if c.status == ClaimStatus.UNKNOWN)
    body.approval_status = ApprovalStatus.REQUIRED
    body.approval_claim_ids = [unknown_claim.id]
    body.external_wait.kind = ExternalWaitKind.KNOWN
    body.external_wait.claim_ids = []
    fixed, coercions, _ = apply_evidence_rules(body, guide.claims)
    assert fixed.approval_status == ApprovalStatus.UNCLEAR
    assert fixed.external_wait.kind == ExternalWaitKind.UNKNOWN
    assert len(coercions) >= 2


def test_step_status_is_weakest_supporting_claim():
    guide = _guide("github")
    body = GuideBody.model_validate(guide.model_dump(include=set(GuideBody.model_fields)))
    inferred = next(c for c in guide.claims if c.status == ClaimStatus.INFERRED)
    documented = next(c for c in guide.claims if c.status == ClaimStatus.OFFICIALLY_DOCUMENTED)
    body.setup_steps[0].claim_ids = [documented.id, inferred.id]
    body.setup_steps[1].claim_ids = []
    fixed, _, _ = apply_evidence_rules(body, guide.claims)
    assert fixed.setup_steps[0].verification_status == ClaimStatus.INFERRED
    assert fixed.setup_steps[1].verification_status == ClaimStatus.INFERRED


def test_supported_claim_ids_are_derived_not_trusted():
    raw = _seed_raw("slack")
    raw["sources"][0]["supported_claim_ids"] = ["C20"]
    guide = build_seed(raw)
    s1 = next(s for s in guide.sources if s.id == "S1")
    assert "C20" not in s1.supported_claim_ids
    assert "C1" in s1.supported_claim_ids
