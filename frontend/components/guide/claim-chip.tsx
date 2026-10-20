"use client";

import { createContext, useContext } from "react";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { CLAIM_STATUS_LABEL } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Claim, ClaimStatus } from "@/types";

type ClaimContextValue = {
  claims: Map<string, Claim>;
  activeClaimId: string | null;
  focusClaim: (id: string) => void;
};

export const ClaimContext = createContext<ClaimContextValue>({
  claims: new Map(),
  activeClaimId: null,
  focusClaim: () => undefined,
});

const DOT: Record<ClaimStatus, string> = {
  tested: "bg-sky-400",
  cross_checked: "bg-teal-400",
  officially_documented: "bg-emerald-400",
  inferred: "bg-amber-400",
  estimated: "bg-violet-400",
  unknown: "bg-zinc-400",
};

export function ClaimChip({ id }: { id: string }) {
  const { claims, activeClaimId, focusClaim } = useContext(ClaimContext);
  const claim = claims.get(id);
  if (!claim) return null;
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          onClick={() => focusClaim(id)}
          aria-label={`Claim ${id}: ${CLAIM_STATUS_LABEL[claim.status]}. Show evidence`}
          className={cn(
            "inline-flex items-center gap-1 rounded border bg-muted/60 px-1 py-px font-mono text-[10px] text-muted-foreground transition-colors hover:border-primary/50 hover:text-foreground",
            activeClaimId === id && "border-primary/60 text-foreground",
          )}
        >
          <span className={cn("size-1.5 rounded-full", DOT[claim.status])} aria-hidden />
          {id}
        </button>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs text-xs">
        <div className="font-medium">{CLAIM_STATUS_LABEL[claim.status]}</div>
        <div>{claim.statement}</div>
      </TooltipContent>
    </Tooltip>
  );
}

export function ClaimChips({ ids, className }: { ids?: string[] | null; className?: string }) {
  if (!ids || ids.length === 0) return null;
  return (
    <span className={cn("inline-flex flex-wrap gap-1", className)}>
      {ids.map((id) => (
        <ClaimChip key={id} id={id} />
      ))}
    </span>
  );
}
