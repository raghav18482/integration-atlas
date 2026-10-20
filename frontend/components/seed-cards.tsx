"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowUpRight } from "lucide-react";

import { ApprovalBadge, OriginBadge } from "@/components/status-badges";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiError } from "@/lib/api";
import { AUTH_LABEL, formatDate, percent } from "@/lib/format";
import type { ApprovalStatus, AuthenticationModel, GuideList } from "@/types";

export function SeedCards() {
  const [items, setItems] = useState<GuideList["items"] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<GuideList>("/api/guides?origin=seed&limit=6")
      .then((r) => setItems(r.items))
      .catch((e: unknown) => setError(e instanceof ApiError ? e.message : "Could not load guides."));
  }, []);

  if (error) {
    return <p role="alert" className="text-sm text-rose-300">{error}</p>;
  }
  if (!items) {
    return (
      <div className="grid gap-3 md:grid-cols-3" aria-busy="true">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-36 rounded-xl" />
        ))}
      </div>
    );
  }
  return (
    <div className="grid gap-3 md:grid-cols-3">
      {items.map((g) => (
        <Link
          key={g.slug}
          href={`/guides/${g.slug}`}
          className="group flex flex-col gap-3 rounded-xl border bg-card p-4 transition-colors hover:border-primary/40 hover:bg-accent/40"
        >
          <div className="flex items-start justify-between gap-2">
            <div>
              <div className="font-medium">{g.provider_name}</div>
              <div className="text-xs text-muted-foreground">
                {AUTH_LABEL[g.authentication_model as AuthenticationModel] ?? g.authentication_model}
              </div>
            </div>
            <ArrowUpRight className="size-4 text-muted-foreground transition-colors group-hover:text-primary" />
          </div>
          <p className="line-clamp-2 text-sm text-muted-foreground">{g.intended_use_case}</p>
          <div className="mt-auto flex flex-wrap items-center gap-1.5">
            <OriginBadge origin={g.origin} />
            {g.approval_status && <ApprovalBadge status={g.approval_status as ApprovalStatus} />}
            <span className="text-[11px] text-muted-foreground">
              Checked {formatDate(g.last_checked_at)} · {percent(g.evidence_coverage)} evidence-backed
            </span>
          </div>
        </Link>
      ))}
    </div>
  );
}
