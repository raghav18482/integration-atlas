"""Seed guides: hand-curated from official docs, validated by the same schema and
evidence rules as live research.

Seed files hold metadata, the guide body, sources, and claims. Derived fields
(step verification status, effort range, checklist, verification report) are
computed here with the same code live research uses, and a seed that would need
any evidence coercion is rejected rather than silently corrected.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.db import repository
from app.db.session import Database
from app.schemas.guide import GuideBody, GuideOrigin, IntegrationGuide
from app.services.guide_generator import apply_evidence_rules, build_checklist, build_report

SEED_DIR = Path(__file__).parent / "guides"
SEED_METHOD = (
    "Seed guide curated by hand from official documentation. Every quote was re-checked "
    "against the live page by scripts/verify_seed_sources.py on the last-checked date. "
    "Not refreshed automatically."
)


def build_seed(data: dict) -> IntegrationGuide:
    data = dict(data)
    data.setdefault("verification_report", {"checked_at": data["last_checked_at"], "method": SEED_METHOD})
    guide = IntegrationGuide.model_validate(data)
    if guide.origin != GuideOrigin.SEED:
        raise ValueError(f"Seed {guide.slug} must have origin 'seed'")
    body, coercions, warnings = apply_evidence_rules(guide, guide.claims)
    if coercions:
        raise ValueError(f"Seed {guide.slug} makes unsupported claims: {coercions}")
    derived = body.model_dump(include=set(GuideBody.model_fields))
    checklist = build_checklist(body.setup_steps)
    report = build_report(
        checked_at=guide.last_checked_at,
        method=SEED_METHOD,
        sources=guide.sources,
        claims=guide.claims,
        mismatches=[],
        coercions=[],
        warnings=warnings,
    )
    full = guide.model_dump()
    full.update(derived)
    full["checklist_state"] = [c.model_dump() for c in checklist]
    full["verification_report"] = report.model_dump()
    for src, original in zip(full["sources"], guide.sources, strict=True):
        src["excerpt"] = original.excerpt
    return IntegrationGuide.model_validate(full)


def load_seed_guides() -> list[IntegrationGuide]:
    return [build_seed(json.loads(p.read_text(encoding="utf-8"))) for p in sorted(SEED_DIR.glob("*.json"))]


async def upsert_seed_guides(db: Database) -> int:
    guides = load_seed_guides()
    async with db.session() as session:
        for guide in guides:
            await repository.save_guide(session, guide)
    return len(guides)
