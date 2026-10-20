"use client";

import { Bot, CheckCircle2, CircleAlert, CircleHelp, Clock, Hourglass, KeyRound, ShieldCheck, User, Users } from "lucide-react";

import { ClaimChips } from "@/components/guide/claim-chip";
import { ApprovalBadge, ClaimStatusBadge, WaitBadge } from "@/components/status-badges";
import { Checkbox } from "@/components/ui/checkbox";
import {
  APPROVAL_KIND_LABEL,
  AUTH_LABEL,
  CONTEXT_LABEL,
  PHASE_LABEL,
  RESPONSIBLE_LABEL,
  SENSITIVITY_LABEL,
  formatHours,
  formatMinutes,
} from "@/lib/format";
import { cn } from "@/lib/utils";
import type { IntegrationContext, IntegrationGuide, SetupStep } from "@/types";

export function Section({
  id,
  title,
  description,
  children,
}: {
  id: string;
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} aria-labelledby={`${id}-title`} className="scroll-mt-20">
      <h2 id={`${id}-title`} className="text-base font-semibold tracking-tight">
        {title}
      </h2>
      {description && <p className="mt-0.5 text-sm text-muted-foreground">{description}</p>}
      <div className="mt-3">{children}</div>
    </section>
  );
}

function Cell({ icon, label, children }: { icon: React.ReactNode; label: string; children: React.ReactNode }) {
  return (
    <div className="bg-card p-3.5">
      <div className="mb-1.5 flex items-center gap-1.5 text-xs text-muted-foreground">
        {icon}
        {label}
      </div>
      {children}
    </div>
  );
}

export function SummaryStrip({ guide }: { guide: IntegrationGuide }) {
  const effort = guide.effort_estimate;
  const wait = guide.external_wait;
  return (
    <div className="grid gap-px overflow-hidden rounded-xl border bg-border sm:grid-cols-2 xl:grid-cols-4" data-testid="summary-strip">
      <Cell icon={<Clock className="size-3.5" />} label="Active developer effort">
        <div className="text-lg font-semibold tabular-nums">{formatHours(effort.low_hours, effort.high_hours)}</div>
        <div className="mt-1 flex items-start gap-1.5">
          <ClaimStatusBadge status="estimated" />
        </div>
        <p className="mt-1.5 text-[11px] leading-snug text-muted-foreground">{effort.basis}</p>
      </Cell>
      <Cell icon={<Hourglass className="size-3.5" />} label="External waiting">
        <div className="text-sm font-medium">{wait.range_text || wait.summary}</div>
        <div className="mt-1 flex flex-wrap items-center gap-1.5">
          <WaitBadge kind={wait.kind} />
          <ClaimChips ids={wait.claim_ids} />
        </div>
        {wait.explanation && <p className="mt-1.5 text-[11px] leading-snug text-muted-foreground">{wait.explanation}</p>}
      </Cell>
      <Cell icon={<ShieldCheck className="size-3.5" />} label="Approval">
        <div className="flex flex-wrap items-center gap-1.5">
          <ApprovalBadge status={guide.approval_status} />
          <ClaimChips ids={guide.approval_claim_ids} />
        </div>
        <p className="mt-1.5 text-[11px] leading-snug text-muted-foreground">{guide.approval_summary}</p>
      </Cell>
      <Cell icon={<KeyRound className="size-3.5" />} label="Authentication model">
        <div className="text-sm font-medium">{AUTH_LABEL[guide.authentication_model]}</div>
        <div className="mt-1">
          <ClaimChips ids={guide.auth_model_claim_ids} />
        </div>
      </Cell>
    </div>
  );
}

export function RecommendedPathSection({ guide }: { guide: IntegrationGuide }) {
  const path = guide.recommended_path;
  return (
    <Section id="overview" title="Overview and recommended path">
      <p className="text-sm leading-relaxed">{guide.overview}</p>
      <p className="mt-3 text-sm text-muted-foreground">{path.summary}</p>
      {path.options && path.options.length > 0 && (
        <div className="mt-3 grid gap-2 md:grid-cols-2">
          {path.options.map((opt) => (
            <div
              key={`${opt.kind}-${opt.title}`}
              className={cn("rounded-lg border p-3", opt.recommended && "border-primary/50 bg-primary/5")}
            >
              <div className="flex items-center justify-between gap-2">
                <div className="text-sm font-medium">{opt.title}</div>
                {opt.recommended && (
                  <span className="rounded bg-primary/15 px-1.5 py-0.5 text-[10px] font-medium text-primary">
                    Recommended
                  </span>
                )}
              </div>
              <p className="mt-1 text-xs text-muted-foreground">{opt.summary}</p>
              {opt.when_to_choose && <p className="mt-1.5 text-xs"><span className="text-muted-foreground">When: </span>{opt.when_to_choose}</p>}
              {opt.tradeoffs && opt.tradeoffs.length > 0 && (
                <ul className="mt-1.5 list-disc pl-4 text-xs text-muted-foreground">
                  {opt.tradeoffs.map((t) => (
                    <li key={t}>{t}</li>
                  ))}
                </ul>
              )}
              <ClaimChips ids={opt.claim_ids} className="mt-2" />
              {(!opt.claim_ids || opt.claim_ids.length === 0) && (
                <p className="mt-2 text-[11px] text-amber-300/80">No source checked for this option.</p>
              )}
            </div>
          ))}
        </div>
      )}
    </Section>
  );
}

export function PrerequisitesSection({ guide }: { guide: IntegrationGuide }) {
  const items = guide.prerequisites ?? [];
  if (items.length === 0) return null;
  return (
    <Section id="prerequisites" title="Prerequisites">
      <ul className="grid gap-2">
        {items.map((p) => (
          <li key={p.title} className="rounded-lg border bg-card px-3 py-2.5">
            <div className="flex flex-wrap items-center gap-2 text-sm font-medium">
              {p.title} <ClaimChips ids={p.claim_ids} />
            </div>
            <p className="mt-0.5 text-sm text-muted-foreground">{p.detail}</p>
          </li>
        ))}
      </ul>
    </Section>
  );
}

const RESPONSIBLE_ICON: Record<string, React.ReactNode> = {
  agent: <Bot className="size-3.5" />,
  developer: <User className="size-3.5" />,
  developer_with_agent: <Users className="size-3.5" />,
};

export function StepCard({
  step,
  index,
  checklistItemId,
  done,
  onToggle,
  stepTitles,
}: {
  step: SetupStep;
  index: number;
  checklistItemId?: string;
  done: boolean;
  onToggle?: (itemId: string, done: boolean) => void;
  stepTitles: Map<string, string>;
}) {
  const effort = formatMinutes(step.active_effort_minutes);
  return (
    <li className={cn("rounded-xl border bg-card p-4", done && "opacity-70")} data-step={step.id}>
      <div className="flex items-start gap-3">
        {checklistItemId && onToggle ? (
          <Checkbox
            checked={done}
            onCheckedChange={(v) => onToggle(checklistItemId, v === true)}
            aria-label={`Mark "${step.title}" complete`}
            className="mt-0.5"
          />
        ) : (
          <span className="mt-0.5 font-mono text-xs text-muted-foreground">{index + 1}</span>
        )}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className={cn("text-sm font-medium", done && "line-through")}>
              <span className="mr-1.5 font-mono text-xs text-muted-foreground">{index + 1}.</span>
              {step.title}
            </h3>
            <ClaimStatusBadge status={step.verification_status ?? "inferred"} />
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
            <span>{PHASE_LABEL[step.phase]}</span>
            <span className="inline-flex items-center gap-1">
              {RESPONSIBLE_ICON[step.responsible] ?? <User className="size-3.5" />}
              {RESPONSIBLE_LABEL[step.responsible]}
            </span>
            {effort ? <span>{effort} hands-on (estimate)</span> : <span>Effort not estimated</span>}
            {step.depends_on && step.depends_on.length > 0 && (
              <span>After: {step.depends_on.map((d) => stepTitles.get(d) ?? d).join(", ")}</span>
            )}
          </div>
          <p className="mt-2 text-sm leading-relaxed">{step.explanation}</p>
          <dl className="mt-2 grid gap-1.5 text-xs sm:grid-cols-2">
            <div>
              <dt className="text-muted-foreground">Why it matters</dt>
              <dd>{step.why_it_matters}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Expected outcome</dt>
              <dd>{step.expected_outcome}</dd>
            </div>
          </dl>
          <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
            {step.claim_ids && step.claim_ids.length > 0 ? (
              <>
                Evidence: <ClaimChips ids={step.claim_ids} />
              </>
            ) : (
              <span className="text-amber-300/80">No cited evidence; general engineering guidance.</span>
            )}
          </div>
        </div>
      </div>
    </li>
  );
}

export function ScopesSection({ guide }: { guide: IntegrationGuide }) {
  const scopes = guide.scopes_or_permissions ?? [];
  return (
    <Section
      id="scopes"
      title="Permissions and scopes"
      description="Only scope names that appear in a cited source are listed by name. Request the narrowest set you can."
    >
      {scopes.length === 0 ? (
        <p className="text-sm text-muted-foreground">No scopes were identified from the sources checked.</p>
      ) : (
        <div className="overflow-hidden rounded-xl border">
          <table className="w-full text-sm">
            <thead className="bg-muted/40 text-left text-xs text-muted-foreground">
              <tr>
                <th className="px-3 py-2 font-medium">Scope / permission</th>
                <th className="px-3 py-2 font-medium">Sensitivity</th>
                <th className="hidden px-3 py-2 font-medium md:table-cell">Needed for</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {scopes.map((s) => (
                <tr key={s.name} className="align-top">
                  <td className="px-3 py-2">
                    <div className="font-mono text-xs">{s.name}</div>
                    <div className="mt-0.5 text-xs text-muted-foreground">{s.description}</div>
                    <ClaimChips ids={s.claim_ids} className="mt-1" />
                  </td>
                  <td className="px-3 py-2 text-xs">{SENSITIVITY_LABEL[s.sensitivity ?? "unknown"]}</td>
                  <td className="hidden px-3 py-2 text-xs text-muted-foreground md:table-cell">{s.needed_for || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Section>
  );
}

export function ApprovalSection({ guide }: { guide: IntegrationGuide }) {
  const items = guide.approval_and_distribution ?? [];
  return (
    <Section
      id="approval"
      title="Approval and launch"
      description="Registration, consent, verification, listing, and production access are separate gates."
    >
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">No approval requirements were identified from the sources checked.</p>
      ) : (
        <ul className="grid gap-2">
          {items.map((a) => (
            <li key={`${a.kind}-${a.title}`} className="rounded-lg border bg-card px-3 py-2.5">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-[11px] uppercase tracking-wide text-muted-foreground">{APPROVAL_KIND_LABEL[a.kind]}</span>
                <span className="text-sm font-medium">{a.title}</span>
                <ApprovalBadge status={a.status} />
                <ClaimChips ids={a.claim_ids} />
              </div>
              {a.applies_when && <p className="mt-1 text-xs text-muted-foreground">Applies when: {a.applies_when}</p>}
              <p className="mt-1 text-sm">{a.description}</p>
              {a.external_wait && (
                <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                  <Hourglass className="size-3.5" /> Wait: {a.external_wait.range_text || a.external_wait.summary}
                  <WaitBadge kind={a.external_wait.kind} />
                  <ClaimChips ids={a.external_wait.claim_ids} />
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

export function TestingSection({ guide }: { guide: IntegrationGuide }) {
  const items = guide.testing_plan ?? [];
  if (items.length === 0) return null;
  return (
    <Section id="testing" title="Testing plan">
      <ul className="grid gap-2">
        {items.map((t) => (
          <li key={t.title} className="flex gap-2 rounded-lg border bg-card px-3 py-2.5">
            <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
            <div>
              <div className="flex flex-wrap items-center gap-2 text-sm font-medium">
                {t.title} <ClaimChips ids={t.claim_ids} />
              </div>
              <p className="text-sm text-muted-foreground">{t.detail}</p>
            </div>
          </li>
        ))}
      </ul>
    </Section>
  );
}

const BLOCKER_ICON = {
  blocker: <CircleAlert className="size-4 text-rose-300" />,
  risk: <CircleAlert className="size-4 text-amber-300" />,
  unknown: <CircleHelp className="size-4 text-zinc-400" />,
};

export function BlockersSection({ guide }: { guide: IntegrationGuide }) {
  const items = guide.blockers_and_unknowns ?? [];
  return (
    <Section id="blockers" title="Blockers and unknowns">
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">None recorded. That is not proof there are none.</p>
      ) : (
        <ul className="grid gap-2">
          {items.map((b) => (
            <li key={b.id} className="flex gap-2.5 rounded-lg border bg-card px-3 py-2.5">
              <span className="mt-0.5">{BLOCKER_ICON[b.kind]}</span>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2 text-sm font-medium">
                  <span className="text-[11px] uppercase tracking-wide text-muted-foreground">{b.kind}</span>
                  {b.title}
                  <ClaimChips ids={b.claim_ids} />
                </div>
                <p className="mt-0.5 text-sm text-muted-foreground">{b.detail}</p>
                {b.mitigation && <p className="mt-1 text-xs"><span className="text-muted-foreground">Mitigation: </span>{b.mitigation}</p>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

export function AgentSection({ guide }: { guide: IntegrationGuide }) {
  const actions = guide.agent_vs_developer_actions ?? [];
  if (actions.length === 0) return null;
  const columns = [
    { key: "agent", title: "An agent can do", icon: <Bot className="size-4 text-primary" /> },
    { key: "both", title: "Agent drafts, you approve", icon: <Users className="size-4 text-violet-300" /> },
    { key: "developer", title: "You must do", icon: <User className="size-4 text-amber-300" /> },
  ] as const;
  return (
    <Section
      id="agent"
      title="What an agent can do vs. where you take over"
      description="Provider consoles, terms, payments, and review submissions need a human with account access."
    >
      <div className="grid gap-2 md:grid-cols-3">
        {columns.map((col) => (
          <div key={col.key} className="rounded-lg border bg-card p-3">
            <div className="mb-2 flex items-center gap-1.5 text-sm font-medium">
              {col.icon}
              {col.title}
            </div>
            <ul className="grid gap-2">
              {actions
                .filter((a) => a.actor === col.key)
                .map((a) => (
                  <li key={a.action} className="text-sm">
                    {a.action}
                    {a.rationale && <div className="text-xs text-muted-foreground">{a.rationale}</div>}
                  </li>
                ))}
            </ul>
          </div>
        ))}
      </div>
    </Section>
  );
}

export function ContextSection({ guide }: { guide: IntegrationGuide }) {
  const variations = guide.context_variations ?? {};
  const entries = Object.entries(variations) as [IntegrationContext, string][];
  if (entries.length === 0) return null;
  entries.sort(([a], [b]) => (a === guide.integration_context ? -1 : b === guide.integration_context ? 1 : 0));
  return (
    <Section id="contexts" title="If your context is different" description="How the requirements change for personal, internal, and multi-user SaaS integrations.">
      <dl className="grid gap-2">
        {entries.map(([ctx, text]) => (
          <div key={ctx} className={cn("rounded-lg border px-3 py-2", ctx === guide.integration_context && "border-primary/40 bg-primary/5")}>
            <dt className="text-xs font-medium">
              {CONTEXT_LABEL[ctx]}
              {ctx === guide.integration_context && <span className="ml-1.5 text-primary">· this guide</span>}
            </dt>
            <dd className="text-sm text-muted-foreground">{text}</dd>
          </div>
        ))}
      </dl>
    </Section>
  );
}

export function VerificationSection({ guide }: { guide: IntegrationGuide }) {
  const r = guide.verification_report;
  const byStatus = Object.entries(r.claims_by_status ?? {});
  return (
    <Section id="verification" title="How this guide was checked" description={r.method}>
      <div className="grid gap-3 rounded-xl border bg-card p-4 text-sm">
        <div className="flex flex-wrap gap-x-6 gap-y-2">
          <span>
            <span className="text-muted-foreground">Sources:</span> {r.sources_retrieved}/{r.sources_total} retrieved
            {r.sources_snippet_only ? `, ${r.sources_snippet_only} snippet-only` : ""}
            {r.sources_failed ? `, ${r.sources_failed} failed` : ""}
          </span>
          <span>
            <span className="text-muted-foreground">Claims:</span> {r.claims_total}
          </span>
          <span>
            <span className="text-muted-foreground">Evidence coverage:</span> {Math.round((r.evidence_coverage ?? 0) * 100)}%
          </span>
        </div>
        {byStatus.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {byStatus.map(([status, n]) => (
              <span key={status} className="inline-flex items-center gap-1 text-xs">
                <ClaimStatusBadge status={status as never} /> {n}
              </span>
            ))}
          </div>
        )}
        {(r.quote_mismatch_claim_ids?.length ?? 0) > 0 && (
          <p className="text-xs text-amber-200">
            Downgraded because the model&apos;s quote was not found in the cited page: <ClaimChips ids={r.quote_mismatch_claim_ids} />
          </p>
        )}
        {(r.coercions?.length ?? 0) > 0 && (
          <div className="text-xs">
            <div className="text-muted-foreground">Conclusions downgraded for lack of evidence:</div>
            <ul className="mt-1 list-disc pl-4">
              {r.coercions!.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          </div>
        )}
        {(r.warnings?.length ?? 0) > 0 && (
          <div className="text-xs">
            <div className="text-muted-foreground">Warnings:</div>
            <ul className="mt-1 list-disc pl-4 text-amber-200/90">
              {r.warnings!.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          </div>
        )}
        <p className="text-xs text-muted-foreground">
          A retrieved page is not a working integration. Only claims marked “Tested” come from requests we actually
          made. Nothing here predicts whether a provider will approve your app.
        </p>
      </div>
    </Section>
  );
}
