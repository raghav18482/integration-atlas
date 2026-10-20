"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Check, Link2, Loader2, RefreshCw } from "lucide-react";
import { toast } from "sonner";

import { ClaimContext } from "@/components/guide/claim-chip";
import { EvidencePanel } from "@/components/guide/evidence-panel";
import {
  AgentSection,
  ApprovalSection,
  BlockersSection,
  ContextSection,
  PrerequisitesSection,
  RecommendedPathSection,
  ScopesSection,
  Section,
  StepCard,
  SummaryStrip,
  TestingSection,
  VerificationSection,
} from "@/components/guide/guide-sections";
import { QaPanel } from "@/components/guide/qa-panel";
import { ReportForm } from "@/components/guide/report-form";
import { OriginBadge, ResearchStatusBadge } from "@/components/status-badges";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, ApiError, openLlmSettings } from "@/lib/api";
import { AUTH_LABEL, CONTEXT_LABEL, formatDateTime, percent } from "@/lib/format";
import type { ChecklistProgress, GuideResponse, ResearchStarted } from "@/types";

const NAV = [
  ["overview", "Overview"],
  ["prerequisites", "Prerequisites"],
  ["steps", "Setup steps"],
  ["scopes", "Permissions and scopes"],
  ["approval", "Approval and launch"],
  ["testing", "Testing"],
  ["blockers", "Blockers and unknowns"],
  ["agent", "Agent vs. developer"],
  ["verification", "How it was checked"],
] as const;

export function GuideWorkspace({ slug }: { slug: string }) {
  const router = useRouter();
  const [data, setData] = useState<GuideResponse | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [progress, setProgress] = useState<ChecklistProgress | null>(null);
  const [activeClaimId, setActiveClaimId] = useState<string | null>(null);
  const [tab, setTab] = useState("evidence");
  const [copied, setCopied] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    api<GuideResponse>(`/api/guides/${slug}`)
      .then((res) => {
        setData(res);
        setProgress(res.checklist_progress);
      })
      .catch((e: unknown) => setError(e instanceof ApiError ? e : new ApiError(0, "unknown", "Could not load the guide.")));
  }, [slug]);

  const claims = useMemo(() => new Map((data?.guide.claims ?? []).map((c) => [c.id, c])), [data]);
  const focusClaim = useCallback((id: string) => {
    setActiveClaimId(id);
    setTab("evidence");
  }, []);

  async function toggle(itemId: string, completed: boolean) {
    const previous = progress;
    if (progress) {
      const items = { ...progress.items, [itemId]: completed };
      setProgress({ ...progress, items, completed: Object.values(items).filter(Boolean).length });
    }
    try {
      setProgress(await api<ChecklistProgress>(`/api/guides/${slug}/checklist`, { method: "PATCH", json: { item_id: itemId, completed } }));
    } catch (e) {
      setProgress(previous);
      toast.error(e instanceof ApiError ? e.message : "Could not save checklist progress.");
    }
  }

  async function copyLink() {
    await navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    toast.success("Guide link copied");
    setTimeout(() => setCopied(false), 2000);
  }

  async function refresh() {
    setRefreshing(true);
    try {
      const res = await api<ResearchStarted>(`/api/guides/${slug}/refresh`, { method: "POST" });
      router.push(`/research/${res.run_id}`);
    } catch (e) {
      setRefreshing(false);
      if (e instanceof ApiError && e.code.startsWith("llm_")) {
        toast.error(e.message, { action: { label: "LLM settings", onClick: openLlmSettings } });
      } else {
        toast.error(e instanceof ApiError ? e.message : "Could not start research.");
      }
    }
  }

  if (error) {
    return (
      <div className="mx-auto max-w-xl py-16 text-center">
        <h1 className="text-xl font-semibold">{error.status === 404 ? "Guide not found" : "Could not load guide"}</h1>
        <p className="mt-2 text-sm text-muted-foreground">{error.message}</p>
        <Button asChild variant="outline" className="mt-4">
          <Link href="/guides">Browse saved guides</Link>
        </Button>
      </div>
    );
  }
  if (!data || !progress) {
    return (
      <div className="grid gap-4 lg:grid-cols-[220px_1fr_360px]" aria-busy="true">
        <Skeleton className="h-80" />
        <Skeleton className="h-[600px]" />
        <Skeleton className="h-80" />
      </div>
    );
  }

  const { guide } = data;
  const checklistByStep = new Map((guide.checklist_state ?? []).map((c) => [c.step_id, c.id]));
  const stepTitles = new Map(guide.setup_steps.map((s) => [s.id, s.title]));
  const coverage = guide.verification_report.evidence_coverage ?? 0;
  const isSeed = guide.origin === "seed";

  return (
    <ClaimContext.Provider value={{ claims, activeClaimId, focusClaim }}>
      <div className="grid gap-6 lg:grid-cols-[220px_minmax(0,1fr)] xl:grid-cols-[220px_minmax(0,1fr)_380px]">
        {/* Left sidebar */}
        <aside className="hidden lg:block">
          <div className="sticky top-20 grid gap-4 text-sm">
            <div>
              <div className="font-semibold">{guide.provider_name}</div>
              <div className="text-xs text-muted-foreground">{AUTH_LABEL[guide.authentication_model]}</div>
              <div className="mt-2 flex flex-wrap gap-1">
                <OriginBadge origin={guide.origin} />
                <ResearchStatusBadge status={guide.research_status} />
              </div>
            </div>
            <nav aria-label="Guide sections" className="grid gap-0.5">
              {NAV.map(([id, label]) => (
                <a key={id} href={`#${id}`} className="rounded px-2 py-1 text-muted-foreground hover:bg-muted hover:text-foreground">
                  {label}
                </a>
              ))}
              <a href="#sources" onClick={() => setTab("evidence")} className="rounded px-2 py-1 text-muted-foreground hover:bg-muted hover:text-foreground">
                Sources
              </a>
            </nav>
            <div className="grid gap-3 rounded-lg border bg-card p-3">
              <div>
                <div className="mb-1 flex justify-between text-xs">
                  <span className="text-muted-foreground">Your checklist</span>
                  <span className="tabular-nums" data-testid="checklist-count">
                    {progress.completed}/{progress.total}
                  </span>
                </div>
                <Progress value={progress.total ? (progress.completed / progress.total) * 100 : 0} aria-label="Checklist progress" />
              </div>
              <div>
                <div className="mb-1 flex justify-between text-xs">
                  <span className="text-muted-foreground">Evidence coverage</span>
                  <span className="tabular-nums">{percent(coverage)}</span>
                </div>
                <Progress value={coverage * 100} aria-label="Evidence coverage" />
                <p className="mt-1 text-[10px] leading-snug text-muted-foreground">
                  Share of claims backed by a retrieved official source or a test. Not an approval likelihood.
                </p>
              </div>
            </div>
          </div>
        </aside>

        {/* Center */}
        <article className="grid min-w-0 gap-8">
          <header className="grid gap-3 border-b pb-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h1 className="text-2xl font-semibold tracking-tight">{guide.provider_name} integration guide</h1>
                <p className="mt-1 text-sm text-muted-foreground">
                  {guide.intended_use_case || "No use case given"} · {CONTEXT_LABEL[guide.integration_context]}
                </p>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={copyLink}>
                  {copied ? <Check /> : <Link2 />} {copied ? "Copied" : "Copy link"}
                </Button>
                <Button variant="outline" size="sm" onClick={refresh} disabled={refreshing}>
                  {refreshing ? <Loader2 className="animate-spin" /> : <RefreshCw />}
                  {isSeed ? "Run live research" : "Re-run research"}
                </Button>
              </div>
            </div>
            <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
              <span>{isSeed ? "Curated" : "Generated"} {formatDateTime(guide.generated_at)}</span>
              <span>Last checked {formatDateTime(guide.last_checked_at)}</span>
              {guide.llm_model && <span>Model {guide.llm_provider} · {guide.llm_model}</span>}
              {guide.seed_parent_slug && (
                <span>
                  Live re-research of <Link href={`/guides/${guide.seed_parent_slug}`} className="text-primary hover:underline">the seed guide</Link>
                </span>
              )}
            </div>
            {isSeed && (
              <p className="rounded-md border border-dashed px-3 py-2 text-xs text-muted-foreground">
                Seed guide: curated by hand from official documentation and re-checked on the date above. It was not
                freshly researched when you opened it. “Run live research” creates a separate, model-generated guide.
              </p>
            )}
            {guide.research_status === "partial" && (
              <p className="rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-100">
                Incomplete evidence. Some requirements could not be verified; see “How it was checked”.
              </p>
            )}
          </header>

          <SummaryStrip guide={guide} />
          <RecommendedPathSection guide={guide} />
          <PrerequisitesSection guide={guide} />

          <Section id="steps" title="Setup steps" description="Tick steps off as you go. Your progress is saved for this browser only.">
            <ol className="grid gap-3">
              {guide.setup_steps.map((step, i) => {
                const itemId = checklistByStep.get(step.id);
                return (
                  <StepCard
                    key={step.id}
                    step={step}
                    index={i}
                    checklistItemId={itemId}
                    done={itemId ? Boolean(progress.items[itemId]) : false}
                    onToggle={toggle}
                    stepTitles={stepTitles}
                  />
                );
              })}
            </ol>
          </Section>

          <ScopesSection guide={guide} />
          <ApprovalSection guide={guide} />
          <TestingSection guide={guide} />
          <BlockersSection guide={guide} />
          <AgentSection guide={guide} />
          <ContextSection guide={guide} />
          <VerificationSection guide={guide} />
        </article>

        {/* Right sidebar */}
        <aside className="min-w-0 lg:col-span-2 xl:col-span-1">
          <div className="xl:sticky xl:top-20">
            <Tabs value={tab} onValueChange={setTab}>
              <TabsList className="w-full">
                <TabsTrigger value="evidence">Evidence</TabsTrigger>
                <TabsTrigger value="ask">Ask</TabsTrigger>
                <TabsTrigger value="report">Report issue</TabsTrigger>
              </TabsList>
              <div className="mt-3 xl:max-h-[calc(100vh-9rem)] xl:overflow-y-auto xl:pr-1">
                <TabsContent value="evidence">
                  <EvidencePanel guide={guide} />
                </TabsContent>
                <TabsContent value="ask" forceMount hidden={tab !== "ask"}>
                  <QaPanel slug={guide.slug} />
                </TabsContent>
                <TabsContent value="report">
                  <ReportForm guide={guide} />
                </TabsContent>
              </div>
            </Tabs>
          </div>
        </aside>
      </div>
    </ClaimContext.Provider>
  );
}
