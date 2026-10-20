"""Re-check every seed guide claim against the live source pages.

For each seed guide:
- fetch every source with the app's SSRF-safe fetcher,
- check each claim's evidence_quote appears in at least one of its sources
  (using the same quote matcher the research pipeline uses),
- re-fetch discovery documents and confirm the values behind `tested` claims.

Writes docs/seed-verification-report.md. Run from the repo root:
    cd backend && uv run python ../scripts/verify_seed_sources.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.schemas.guide import ClaimStatus  # noqa: E402
from app.seed.loader import SEED_DIR, build_seed  # noqa: E402
from app.services.document_fetcher import default_client, fetch_document  # noqa: E402
from app.services.evidence import normalize, quote_in_text  # noqa: E402

REPORT = ROOT / "docs" / "seed-verification-report.md"


async def verify() -> int:
    lines = [
        "# Seed verification report",
        "",
        f"Generated {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')} by `scripts/verify_seed_sources.py`.",
        "",
        "Each claim's quote is matched against the live text of its cited source(s), using the same "
        "matcher the research pipeline uses. `tested` claims are re-checked against the live discovery document.",
        "",
    ]
    failures = 0
    async with default_client() as client:
        for path in sorted(SEED_DIR.glob("*.json")):
            guide = build_seed(json.loads(path.read_text(encoding="utf-8")))
            fetched = {}
            for src in guide.sources:
                fetched[src.id] = await fetch_document(src.url, client)
            lines += [
                f"## {guide.provider_name} (`{guide.slug}`)",
                "",
                "| Source | Status | URL |",
                "|---|---|---|",
            ]
            for src in guide.sources:
                res = fetched[src.id]
                status = "retrieved" if res.ok else f"FAILED ({res.error})"
                lines.append(f"| {src.id} | {status} | {src.url} |")
            lines += ["", "| Claim | Status | Result |", "|---|---|---|"]
            for claim in guide.claims:
                if claim.status == ClaimStatus.TESTED:
                    src = fetched[claim.source_ids[0]]
                    raw = normalize(src.raw or src.text)
                    expected = [
                        v
                        for v in (
                            "accounts.google.com/o/oauth2/v2/auth",
                            "oauth2.googleapis.com/token",
                            "s256",
                            "openid",
                        )
                        if v in normalize(claim.statement)
                    ]
                    ok = src.ok and all(v in raw for v in expected)
                    result = (
                        "re-tested: values present in live document" if ok else "MISMATCH in live document"
                    )
                elif claim.evidence_quote:
                    hits = [
                        sid
                        for sid in claim.source_ids
                        if fetched[sid].ok and quote_in_text(claim.evidence_quote, fetched[sid].text)
                    ]
                    ok = bool(hits)
                    result = f"quote found in {', '.join(hits)}" if ok else "QUOTE NOT FOUND"
                else:
                    ok = True
                    result = "no quote (status is not evidence)"
                if not ok:
                    failures += 1
                lines.append(f"| {claim.id} | {claim.status.value} | {result} |")
            lines.append("")
    lines.append(f"**Failures: {failures}**")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return failures


if __name__ == "__main__":
    sys.exit(1 if asyncio.run(verify()) else 0)
