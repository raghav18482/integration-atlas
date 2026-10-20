"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useId, useState } from "react";
import { ArrowRight, Loader2, Lock } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api, ApiError, openLlmSettings } from "@/lib/api";
import { CONTEXT_HELP, CONTEXT_LABEL } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { GuideList, IntegrationContext, ResearchStarted } from "@/types";

const CONTEXTS: IntegrationContext[] = ["personal", "internal", "multi_tenant_saas"];

type ErrorState = { message: string; code: string } | null;

export function DiscoveryForm() {
  const router = useRouter();
  const ids = { query: useId(), useCase: useId(), extra: useId() };
  const [query, setQuery] = useState("");
  const [useCase, setUseCase] = useState("");
  const [context, setContext] = useState<IntegrationContext>("multi_tenant_saas");
  const [extra, setExtra] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<ErrorState>(null);
  const [existing, setExisting] = useState<GuideList["items"]>([]);

  // Hint at saved guides for the same app (debounced, best effort).
  const hintable = query.trim().length >= 3 && !query.includes("/");
  const matches = hintable ? existing : [];
  useEffect(() => {
    const q = query.trim();
    if (q.length < 3 || q.includes("/")) return;
    const controller = new AbortController();
    const t = setTimeout(() => {
      api<GuideList>(`/api/guides?q=${encodeURIComponent(q)}&limit=3`, { signal: controller.signal })
        .then((r) => setExisting(r.items))
        .catch(() => undefined);
    }, 300);
    return () => {
      clearTimeout(t);
      controller.abort();
    };
  }, [query]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await api<ResearchStarted>("/api/research", {
        method: "POST",
        json: {
          query: query.trim(),
          intended_use_case: useCase.trim(),
          integration_context: context,
          additional_context: extra.trim(),
        },
      });
      router.push(`/research/${res.run_id}`);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? { message: err.message, code: err.code }
          : { message: "Something went wrong.", code: "unknown" },
      );
      setSubmitting(false);
    }
  }

  const needsLlm = error && ["llm_not_configured", "llm_session_expired"].includes(error.code);

  return (
    <form onSubmit={submit} className="grid gap-4 rounded-xl border bg-card p-5 shadow-sm" aria-label="Generate integration guide">
      <div className="grid gap-1.5">
        <Label htmlFor={ids.query}>Application name or documentation URL</Label>
        <Input
          id={ids.query}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. Notion, Zoom, or https://developers.hubspot.com/docs/api/oauth-quickstart-guide"
          required
          minLength={2}
          autoComplete="off"
          className="h-10"
        />
        {matches.length > 0 && (
          <p className="text-xs text-muted-foreground">
            Saved guide{matches.length > 1 ? "s" : ""} available:{" "}
            {matches.map((g, i) => (
              <span key={g.slug}>
                {i > 0 && ", "}
                <Link className="text-primary hover:underline" href={`/guides/${g.slug}`}>
                  {g.provider_name}
                </Link>
              </span>
            ))}
            . You can still run fresh research.
          </p>
        )}
      </div>

      <div className="grid gap-1.5">
        <Label htmlFor={ids.useCase}>Intended use case <span className="text-muted-foreground">(optional)</span></Label>
        <Input
          id={ids.useCase}
          value={useCase}
          onChange={(e) => setUseCase(e.target.value)}
          placeholder="e.g. An agent that reads support tickets and drafts replies"
          maxLength={1000}
        />
      </div>

      <fieldset className="grid gap-1.5">
        <legend className="mb-1.5 text-sm font-medium">Integration context</legend>
        <div className="grid gap-2 sm:grid-cols-3" role="radiogroup" aria-label="Integration context">
          {CONTEXTS.map((c) => (
            <button
              key={c}
              type="button"
              role="radio"
              aria-checked={context === c}
              onClick={() => setContext(c)}
              className={cn(
                "rounded-lg border px-3 py-2 text-left text-sm transition-colors hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
                context === c && "border-primary/60 bg-primary/10",
              )}
            >
              <div className="font-medium">{CONTEXT_LABEL[c]}</div>
              <div className="text-xs text-muted-foreground">{CONTEXT_HELP[c]}</div>
            </button>
          ))}
        </div>
      </fieldset>

      <div className="grid gap-1.5">
        <Label htmlFor={ids.extra}>Additional context <span className="text-muted-foreground">(optional)</span></Label>
        <Textarea
          id={ids.extra}
          value={extra}
          onChange={(e) => setExtra(e.target.value)}
          placeholder="Data you need, regions, plans you're on, deadlines…"
          rows={2}
          maxLength={2000}
        />
      </div>

      {error && (
        <div role="alert" className="rounded-md border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
          {error.message}
          {needsLlm && (
            <button type="button" onClick={openLlmSettings} className="ml-1 font-medium text-rose-100 underline">
              Open LLM settings
            </button>
          )}
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Lock className="size-3.5" /> No provider secrets required to research setup requirements.
        </p>
        <Button type="submit" size="lg" disabled={submitting || query.trim().length < 2}>
          {submitting ? <Loader2 className="animate-spin" /> : <ArrowRight />}
          Generate integration guide
        </Button>
      </div>
    </form>
  );
}
