"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Search } from "lucide-react";

import { OriginBadge, ResearchStatusBadge } from "@/components/status-badges";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, ApiError } from "@/lib/api";
import { AUTH_LABEL, CONTEXT_LABEL, formatDate, percent } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { AuthenticationModel, GuideList, IntegrationContext } from "@/types";

const PAGE = 20;
const ORIGINS = [
  { value: "", label: "All" },
  { value: "seed", label: "Seed" },
  { value: "live_research", label: "Live research" },
];

export function SavedGuides() {
  const [q, setQ] = useState("");
  const [origin, setOrigin] = useState("");
  const [data, setData] = useState<GuideList | null>(null);
  const [limit, setLimit] = useState(PAGE);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const t = setTimeout(() => {
      const params = new URLSearchParams({ limit: String(limit) });
      if (q.trim()) params.set("q", q.trim());
      if (origin) params.set("origin", origin);
      api<GuideList>(`/api/guides?${params}`, { signal: controller.signal })
        .then((r) => {
          setData(r);
          setError(null);
        })
        .catch((e: unknown) => {
          if (e instanceof DOMException) return;
          setError(e instanceof ApiError ? e.message : "Could not load guides.");
        });
    }, 200);
    return () => {
      clearTimeout(t);
      controller.abort();
    };
  }, [q, origin, limit]);

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative max-w-sm flex-1">
          <Search className="absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setLimit(PAGE);
            }}
            placeholder="Search by provider or use case"
            className="pl-8"
            aria-label="Search guides"
          />
        </div>
        <div className="flex rounded-lg border p-0.5" role="group" aria-label="Filter by origin">
          {ORIGINS.map((o) => (
            <button
              key={o.value}
              type="button"
              onClick={() => setOrigin(o.value)}
              aria-pressed={origin === o.value}
              className={cn(
                "rounded-md px-2.5 py-1 text-xs text-muted-foreground hover:text-foreground",
                origin === o.value && "bg-muted text-foreground",
              )}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>

      {error && <p role="alert" className="text-sm text-rose-300">{error}</p>}

      <div className="overflow-hidden rounded-xl border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Provider</TableHead>
              <TableHead>Auth</TableHead>
              <TableHead className="hidden lg:table-cell">Intended use</TableHead>
              <TableHead className="hidden md:table-cell">Context</TableHead>
              <TableHead className="hidden md:table-cell">Generated</TableHead>
              <TableHead>Last checked</TableHead>
              <TableHead>Evidence</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {!data &&
              [0, 1, 2].map((i) => (
                <TableRow key={i}>
                  <TableCell colSpan={7}>
                    <Skeleton className="h-6" />
                  </TableCell>
                </TableRow>
              ))}
            {data?.items.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="py-8 text-center text-sm text-muted-foreground">
                  No guides match. Try another search, or <Link href="/" className="text-primary hover:underline">research a new app</Link>.
                </TableCell>
              </TableRow>
            )}
            {data?.items.map((g) => (
              <TableRow key={g.slug}>
                <TableCell>
                  <Link href={`/guides/${g.slug}`} className="font-medium hover:text-primary">
                    {g.provider_name}
                  </Link>
                  <div className="mt-1">
                    <OriginBadge origin={g.origin} />
                  </div>
                </TableCell>
                <TableCell className="text-sm">{AUTH_LABEL[g.authentication_model as AuthenticationModel] ?? g.authentication_model}</TableCell>
                <TableCell className="hidden max-w-[280px] truncate text-sm text-muted-foreground lg:table-cell">
                  {g.intended_use_case || "—"}
                </TableCell>
                <TableCell className="hidden text-sm md:table-cell">
                  {CONTEXT_LABEL[g.integration_context as IntegrationContext] ?? g.integration_context}
                </TableCell>
                <TableCell className="hidden text-sm text-muted-foreground md:table-cell">{formatDate(g.generated_at)}</TableCell>
                <TableCell className="text-sm text-muted-foreground">{formatDate(g.last_checked_at)}</TableCell>
                <TableCell>
                  <div className="flex flex-col items-start gap-1">
                    <ResearchStatusBadge status={g.research_status} />
                    <span className="text-[11px] text-muted-foreground">
                      {percent(g.evidence_coverage)} of {g.claims_total} claims backed · {g.sources_total} sources
                    </span>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      {data && data.total > data.items.length && (
        <Button variant="outline" className="justify-self-center" onClick={() => setLimit((l) => l + PAGE)}>
          Load more ({data.total - data.items.length} remaining)
        </Button>
      )}
    </div>
  );
}
