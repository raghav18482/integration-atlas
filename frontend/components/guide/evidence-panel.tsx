"use client";

import { useContext, useEffect, useRef } from "react";
import { ExternalLink, FlaskConical, Quote } from "lucide-react";

import { ClaimChips, ClaimContext } from "@/components/guide/claim-chip";
import { ClaimStatusBadge, RetrievalBadge } from "@/components/status-badges";
import { SOURCE_TYPE_LABEL, formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { IntegrationGuide } from "@/types";

export function EvidencePanel({ guide }: { guide: IntegrationGuide }) {
  const { activeClaimId } = useContext(ClaimContext);
  const refs = useRef(new Map<string, HTMLLIElement>());
  const sourcesById = new Map(guide.sources?.map((s) => [s.id, s]) ?? []);

  useEffect(() => {
    if (activeClaimId) refs.current.get(activeClaimId)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [activeClaimId]);

  return (
    <div className="grid gap-5">
      <div>
        <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Claims</h3>
        <ul className="grid gap-2">
          {(guide.claims ?? []).map((c) => (
            <li
              key={c.id}
              ref={(el) => {
                if (el) refs.current.set(c.id, el);
              }}
              className={cn(
                "rounded-lg border bg-card p-2.5 text-sm transition-colors",
                activeClaimId === c.id && "border-primary/60 ring-1 ring-primary/40",
              )}
              data-claim={c.id}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-[11px] text-muted-foreground">{c.id}</span>
                <ClaimStatusBadge status={c.status} />
              </div>
              <p className="mt-1">{c.statement}</p>
              {c.evidence_quote && (
                <blockquote className="mt-1.5 flex gap-1.5 border-l-2 border-emerald-500/40 pl-2 text-xs text-muted-foreground">
                  <Quote className="mt-0.5 size-3 shrink-0" />
                  <span>{c.evidence_quote}</span>
                </blockquote>
              )}
              {c.test_detail && (
                <p className="mt-1.5 flex gap-1.5 text-xs text-sky-200/90">
                  <FlaskConical className="mt-0.5 size-3 shrink-0" />
                  {c.test_detail}
                </p>
              )}
              {c.note && <p className="mt-1 text-xs text-amber-200/80">{c.note}</p>}
              {c.source_ids && c.source_ids.length > 0 && (
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {c.source_ids.map((sid) => {
                    const s = sourcesById.get(sid);
                    return s ? (
                      <a
                        key={sid}
                        href={s.url}
                        target="_blank"
                        rel="noreferrer noopener"
                        className="inline-flex items-center gap-1 rounded border px-1 py-px text-[11px] text-muted-foreground hover:text-primary"
                      >
                        {sid} · {s.domain} <ExternalLink className="size-2.5" />
                      </a>
                    ) : null;
                  })}
                </div>
              )}
            </li>
          ))}
        </ul>
      </div>

      <div>
        <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Sources</h3>
        <ul className="grid gap-2" id="sources">
          {(guide.sources ?? []).map((s) => (
            <li key={s.id} className="rounded-lg border bg-card p-2.5">
              <div className="flex items-start justify-between gap-2">
                <a
                  href={s.url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="min-w-0 text-sm hover:text-primary"
                >
                  <span className="mr-1 font-mono text-[11px] text-muted-foreground">{s.id}</span>
                  {s.title}
                  <ExternalLink className="ml-1 inline size-3 text-muted-foreground" />
                </a>
                <RetrievalBadge status={s.retrieval_status} />
              </div>
              <div className="mt-1 flex flex-wrap gap-x-2 text-[11px] text-muted-foreground">
                <span>{s.domain}</span>
                <span>{SOURCE_TYPE_LABEL[s.source_type]}</span>
                {s.accessed_at && <span>accessed {formatDate(s.accessed_at)}</span>}
              </div>
              {s.error && <p className="mt-1 text-[11px] text-amber-200/80">{s.error}</p>}
              {s.supported_claim_ids && s.supported_claim_ids.length > 0 ? (
                <div className="mt-1.5 flex flex-wrap items-center gap-1 text-[11px] text-muted-foreground">
                  Supports <ClaimChips ids={s.supported_claim_ids} />
                </div>
              ) : (
                <p className="mt-1.5 text-[11px] text-muted-foreground">No claims rely on this source.</p>
              )}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
