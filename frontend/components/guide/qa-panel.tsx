"use client";

import { useState } from "react";
import { Loader2, Send } from "lucide-react";

import { ClaimChips } from "@/components/guide/claim-chip";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { api, ApiError, openLlmSettings } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ChatResponse, ChatTurn } from "@/types";

const SUGGESTIONS = [
  "Which scopes are necessary?",
  "Why does this need verification?",
  "Which steps require manual action?",
  "What remains uncertain?",
];

type Entry = { question: string; answer?: ChatResponse; error?: { message: string; code: string } };

const GROUNDING_LABEL = {
  grounded: { text: "Grounded in this guide's evidence", tone: "text-emerald-300" },
  partial: { text: "Partly supported; check the cited claims", tone: "text-amber-300" },
  insufficient: { text: "Not enough evidence in this guide", tone: "text-rose-300" },
} as const;

export function QaPanel({ slug }: { slug: string }) {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);

  async function ask(q: string) {
    const text = q.trim();
    if (text.length < 2 || busy) return;
    setBusy(true);
    setQuestion("");
    const history: ChatTurn[] = entries
      .filter((e) => e.answer)
      .slice(-2)
      .flatMap((e) => [
        { role: "user" as const, content: e.question },
        { role: "assistant" as const, content: e.answer!.answer },
      ]);
    setEntries((prev) => [...prev, { question: text }]);
    try {
      const answer = await api<ChatResponse>(`/api/guides/${slug}/chat`, {
        method: "POST",
        json: { question: text, history },
      });
      setEntries((prev) => prev.map((e, i) => (i === prev.length - 1 ? { ...e, answer } : e)));
    } catch (err) {
      const error =
        err instanceof ApiError ? { message: err.message, code: err.code } : { message: "Request failed.", code: "unknown" };
      setEntries((prev) => prev.map((e, i) => (i === prev.length - 1 ? { ...e, error } : e)));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-3">
      <p className="text-xs text-muted-foreground">
        Answers use only this guide, its claims, and its source excerpts. This conversation is not saved; only the
        last two exchanges are sent with each question.
      </p>
      {entries.length === 0 && (
        <div className="flex flex-wrap gap-1.5">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => ask(s)}
              className="rounded-full border px-2.5 py-1 text-xs text-muted-foreground hover:border-primary/50 hover:text-foreground"
            >
              {s}
            </button>
          ))}
        </div>
      )}
      <ol className="grid gap-3" aria-live="polite">
        {entries.map((e, i) => (
          <li key={i} className="grid gap-1.5">
            <div className="justify-self-end rounded-lg bg-primary/15 px-3 py-1.5 text-sm">{e.question}</div>
            {!e.answer && !e.error && (
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Loader2 className="size-3.5 animate-spin" /> Reading the guide…
              </div>
            )}
            {e.error && (
              <div role="alert" className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
                {e.error.message}
                {e.error.code.startsWith("llm_") && (
                  <button type="button" className="ml-1 underline" onClick={openLlmSettings}>
                    Open LLM settings
                  </button>
                )}
              </div>
            )}
            {e.answer && (
              <div className="rounded-lg border bg-card px-3 py-2 text-sm">
                <p className="whitespace-pre-wrap leading-relaxed">{e.answer.answer}</p>
                <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px]">
                  <span className={cn(GROUNDING_LABEL[e.answer.grounding].tone)}>
                    {GROUNDING_LABEL[e.answer.grounding].text}
                  </span>
                  <ClaimChips ids={e.answer.cited_claim_ids} />
                  {e.answer.cited_source_ids.length > 0 && (
                    <span className="text-muted-foreground">Sources: {e.answer.cited_source_ids.join(", ")}</span>
                  )}
                </div>
                {e.answer.needs_fresh_research && (
                  <p className="mt-1 text-[11px] text-amber-200/80">
                    This likely needs fresh research. Use “Re-run research” at the top of the guide.
                  </p>
                )}
                <p className="mt-1 text-[10px] text-muted-foreground">
                  {e.answer.llm.provider} · {e.answer.llm.model} ({e.answer.llm.source === "session" ? "your key" : "app default"})
                </p>
              </div>
            )}
          </li>
        ))}
      </ol>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(question);
        }}
        className="grid gap-2"
      >
        <Textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask about this guide…"
          rows={2}
          maxLength={1000}
          aria-label="Question about this guide"
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              ask(question);
            }
          }}
        />
        <Button type="submit" size="sm" className="justify-self-end" disabled={busy || question.trim().length < 2}>
          {busy ? <Loader2 className="animate-spin" /> : <Send />} Ask
        </Button>
      </form>
    </div>
  );
}
