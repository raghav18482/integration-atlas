"use client";

import { useId, useState } from "react";
import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { api, ApiError } from "@/lib/api";
import type { IntegrationGuide } from "@/types";

const GENERAL = "__general__";

export function ReportForm({ guide }: { guide: IntegrationGuide }) {
  const ids = { target: useId(), message: useId() };
  const [target, setTarget] = useState(GENERAL);
  const [message, setMessage] = useState("");
  const [state, setState] = useState<"idle" | "sending" | "sent">("idle");
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setState("sending");
    setError(null);
    try {
      await api(`/api/guides/${guide.slug}/reports`, {
        method: "POST",
        json: { target_id: target === GENERAL ? null : target, message: message.trim() },
      });
      setState("sent");
      setMessage("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not send the report.");
      setState("idle");
    }
  }

  if (state === "sent") {
    return (
      <div className="grid gap-2 text-sm">
        <p className="text-emerald-300">Thanks. Your report is saved for review.</p>
        <Button variant="outline" size="sm" className="justify-self-start" onClick={() => setState("idle")}>
          Report something else
        </Button>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="grid gap-3">
      <p className="text-xs text-muted-foreground">
        Found a step that is wrong or out of date? Reports are stored with the guide; they don&apos;t change it
        automatically.
      </p>
      <div className="grid gap-1.5">
        <Label htmlFor={ids.target}>What is incorrect?</Label>
        <Select value={target} onValueChange={setTarget}>
          <SelectTrigger id={ids.target} className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={GENERAL}>The guide in general</SelectItem>
            {(guide.setup_steps ?? []).map((s, i) => (
              <SelectItem key={s.id} value={s.id}>
                Step {i + 1}: {s.title}
              </SelectItem>
            ))}
            {(guide.claims ?? []).map((c) => (
              <SelectItem key={c.id} value={c.id}>
                Claim {c.id}: {c.statement.slice(0, 60)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="grid gap-1.5">
        <Label htmlFor={ids.message}>Details</Label>
        <Textarea
          id={ids.message}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          rows={4}
          minLength={5}
          maxLength={2000}
          placeholder="What did you see instead? A link to the current docs helps."
          required
        />
      </div>
      {error && <p role="alert" className="text-sm text-rose-300">{error}</p>}
      <Button type="submit" size="sm" className="justify-self-end" disabled={state === "sending" || message.trim().length < 5}>
        {state === "sending" && <Loader2 className="animate-spin" />} Send report
      </Button>
    </form>
  );
}
