"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AlertTriangle, ArrowRight, Check, Circle, ExternalLink, Loader2, MinusCircle, RotateCcw, XCircle } from "lucide-react";

import { ResearchStatusBadge, RetrievalBadge } from "@/components/status-badges";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiError, openLlmSettings } from "@/lib/api";
import { CONTEXT_LABEL, formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { ResearchEvent, ResearchRun, ResearchStarted } from "@/types";

const TERMINAL = new Set(["completed", "partial", "failed"]);
const POLL_MS = 1500;

type StageState = "pending" | "active" | "done" | "warning" | "failed" | "skipped";

export function stageState(run: ResearchRun, key: string, events: ResearchEvent[]): StageState {
  if (events.some((e) => e.status === "failed")) return "failed";
  if (events.some((e) => e.status === "skipped")) return "skipped";
  if (events.some((e) => e.status === "completed")) {
    return events.some((e) => e.status === "warning") ? "warning" : "done";
  }
  if (events.some((e) => e.status === "warning") && run.stage !== key) return "warning";
  if (events.length > 0) return TERMINAL.has(run.status) ? "warning" : "active";
  return "pending";
}

const STAGE_ICON: Record<StageState, React.ReactNode> = {
  pending: <Circle className="size-4 text-muted-foreground/50" />,
  active: <Loader2 className="size-4 animate-spin text-sky-300" />,
  done: <Check className="size-4 text-emerald-300" />,
  warning: <AlertTriangle className="size-4 text-amber-300" />,
  failed: <XCircle className="size-4 text-rose-300" />,
  skipped: <MinusCircle className="size-4 text-muted-foreground" />,
};

export function ResearchWorkspace({ runId }: { runId: string }) {
  const router = useRouter();
  const [run, setRun] = useState<ResearchRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);

  // Poll the real run record until it reaches a terminal state.
  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function tick() {
      try {
        const data = await api<ResearchRun>(`/api/research/${runId}`);
        if (cancelled) return;
        setRun(data);
        setError(null);
        if (!TERMINAL.has(data.status)) timer = setTimeout(tick, POLL_MS);
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof ApiError ? e.message : "Could not load research status.");
        if (!(e instanceof ApiError && e.status === 404)) timer = setTimeout(tick, POLL_MS * 2);
      }
    }

    tick();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [runId]);

  async function retry() {
    setRetrying(true);
    try {
      const res = await api<ResearchStarted>(`/api/research/${runId}/retry`, { method: "POST" });
      router.push(`/research/${res.run_id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Retry failed.");
      setRetrying(false);
    }
  }

  if (!run) {
    return error ? (
      <div role="alert" className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">{error}</div>
    ) : (
      <div className="grid gap-3" aria-busy="true">
        <Skeleton className="h-16" />
        <Skeleton className="h-72" />
      </div>
    );
  }

  const byStage = new Map<string, ResearchEvent[]>();
  for (const e of run.events) byStage.set(e.stage, [...(byStage.get(e.stage) ?? []), e]);
  const counts = run.sources.reduce<Record<string, number>>((acc, s) => {
    acc[s.status] = (acc[s.status] ?? 0) + 1;
    return acc;
  }, {});
  const llmError = run.error_code?.startsWith("llm_");

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b pb-5">
        <div>
          <p className="text-xs uppercase tracking-wider text-muted-foreground">Research</p>
          <h1 className="text-2xl font-semibold tracking-tight">{run.provider_name ?? run.query}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Input “{run.query}” · {CONTEXT_LABEL[run.integration_context]}
            {run.intended_use_case ? ` · ${run.intended_use_case}` : ""}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Model: {run.llm.provider} · {run.llm.model} ({run.llm.source === "session" ? "your key" : "app default"}) ·
            started {formatDateTime(run.created_at)}
            {run.finished_at ? ` · finished ${formatDateTime(run.finished_at)}` : ""}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <ResearchStatusBadge status={run.status} />
          {run.guide_slug && (
            <Button asChild>
              <Link href={`/guides/${run.guide_slug}`}>
                Open guide <ArrowRight />
              </Link>
            </Button>
          )}
        </div>
      </div>

      {run.status === "partial" && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-100">
          Research finished with incomplete evidence. The guide is saved and marks what could not be verified.
          {run.error_message ? ` ${run.error_message}` : ""}
        </div>
      )}
      {run.status === "failed" && (
        <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-100">
          <span>
            <strong className="font-medium">Research failed.</strong> {run.error_message}
          </span>
          <span className="flex gap-2">
            {llmError && (
              <Button size="sm" variant="outline" onClick={openLlmSettings}>
                LLM settings
              </Button>
            )}
            <Button size="sm" variant="outline" onClick={retry} disabled={retrying}>
              {retrying ? <Loader2 className="animate-spin" /> : <RotateCcw />} Retry
            </Button>
          </span>
        </div>
      )}
      {error && <p className="text-xs text-amber-300">{error} Retrying…</p>}

      <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
        <section aria-label="Research stages" className="rounded-xl border bg-card">
          <h2 className="border-b px-4 py-3 text-sm font-medium">Stages</h2>
          <ol className="divide-y">
            {run.stages.map((stage) => {
              const events = byStage.get(stage.key) ?? [];
              const state = stageState(run, stage.key, events);
              return (
                <li key={stage.key} className="flex gap-3 px-4 py-3" data-stage={stage.key} data-state={state}>
                  <div className="pt-0.5">{STAGE_ICON[state]}</div>
                  <div className="min-w-0 flex-1">
                    <div className={cn("text-sm", state === "pending" ? "text-muted-foreground" : "font-medium")}>
                      {stage.label}
                    </div>
                    {events.length > 0 && (
                      <ul className="mt-1 grid gap-0.5">
                        {events.map((e, i) => (
                          <li
                            key={`${e.ts}-${i}`}
                            className={cn(
                              "text-xs text-muted-foreground",
                              e.status === "failed" && "text-rose-300",
                              e.status === "warning" && "text-amber-300",
                            )}
                          >
                            {e.message}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </li>
              );
            })}
          </ol>
        </section>

        <section aria-label="Sources" className="rounded-xl border bg-card">
          <div className="border-b px-4 py-3">
            <h2 className="text-sm font-medium">Sources</h2>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {run.sources.length} discovered · {counts.retrieved ?? 0} retrieved · {counts.snippet_only ?? 0} snippet only ·{" "}
              {(counts.failed ?? 0) + (counts.blocked ?? 0)} failed
            </p>
          </div>
          {run.sources.length === 0 ? (
            <p className="px-4 py-6 text-sm text-muted-foreground">
              {TERMINAL.has(run.status) ? "No sources were found." : "Waiting for search results…"}
            </p>
          ) : (
            <ul className="max-h-[520px] divide-y overflow-y-auto">
              {run.sources.map((s) => (
                <li key={s.url} className="px-4 py-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <a
                      href={s.url}
                      target="_blank"
                      rel="noreferrer noopener"
                      className="flex min-w-0 items-center gap-1 text-sm hover:text-primary"
                    >
                      {s.id && <span className="font-mono text-xs text-muted-foreground">{s.id}</span>}
                      <span className="truncate">{s.title || s.url}</span>
                      <ExternalLink className="size-3 shrink-0 text-muted-foreground" />
                    </a>
                    <RetrievalBadge status={s.status} />
                  </div>
                  <div className="mt-0.5 flex gap-2 text-[11px] text-muted-foreground">
                    <span>{s.domain}</span>
                    <span>{s.official ? "official" : "secondary"}</span>
                    {s.error && <span className="truncate text-amber-300/90">{s.error}</span>}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
