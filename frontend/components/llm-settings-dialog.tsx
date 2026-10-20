"use client";

import { useCallback, useEffect, useId, useState } from "react";
import { CheckCircle2, KeyRound, Loader2, ShieldCheck, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api, ApiError, notifyLlmConfigChanged } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { LLMConfigStatus, LLMTestResult, ModelsResponse, ProvidersResponse } from "@/types";

type Props = { open: boolean; onOpenChange: (open: boolean) => void };

type Feedback = { tone: "ok" | "error"; text: string } | null;

export function describeConfig(status: LLMConfigStatus | null): string {
  if (!status) return "Checking…";
  switch (status.source) {
    case "session":
      return `Your key · ${status.provider_label} · ${status.model}`;
    case "default":
      return `App default · ${status.provider_label} · ${status.model}`;
    case "expired":
      return "Your session key expired";
    default:
      return "No model configured";
  }
}

export function LlmSettingsDialog({ open, onOpenChange }: Props) {
  const ids = { provider: useId(), model: useId(), key: useId(), test: useId(), models: useId() };
  const [status, setStatus] = useState<LLMConfigStatus | null>(null);
  const [providers, setProviders] = useState<ProvidersResponse | null>(null);
  const [provider, setProvider] = useState("openrouter");
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [testFirst, setTestFirst] = useState(true);
  const [busy, setBusy] = useState<null | "save" | "test" | "clear" | "models">(null);
  const [feedback, setFeedback] = useState<Feedback>(null);
  const [liveModels, setLiveModels] = useState<string[] | null>(null);

  const refresh = useCallback(async () => {
    setStatus(await api<LLMConfigStatus>("/api/session/llm-config"));
  }, []);

  // Load status and provider options each time the dialog opens.
  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    Promise.all([api<LLMConfigStatus>("/api/session/llm-config"), api<ProvidersResponse>("/api/llm/providers")])
      .then(([s, p]) => {
        if (cancelled) return;
        setStatus(s);
        setProviders(p);
        setFeedback(null);
        // Pre-fill a real model ID for the selected provider the first time.
        setModel((current) => current || (p.providers.find((x) => x.id === provider)?.suggested_models[0] ?? ""));
      })
      .catch((e: unknown) => {
        if (!cancelled) setFeedback({ tone: "error", text: e instanceof ApiError ? e.message : "Could not load settings." });
      });
    return () => {
      cancelled = true;
    };
    // Reload only when the dialog opens, not on every provider change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const selected = providers?.providers.find((p) => p.id === provider);
  const suggestions = liveModels ?? selected?.suggested_models ?? [];

  function changeProvider(next: string) {
    setProvider(next);
    setLiveModels(null);
    const info = providers?.providers.find((p) => p.id === next);
    setModel(info?.suggested_models[0] ?? "");
  }

  async function loadModels() {
    setBusy("models");
    try {
      const res = await api<ModelsResponse>(`/api/llm/models?provider=${encodeURIComponent(provider)}`);
      setLiveModels(res.models);
      setFeedback({
        tone: "ok",
        text:
          res.source === "live"
            ? `Loaded ${res.models.length} models from ${selected?.label}.`
            : "Showing suggested models. Save a key for this provider to list its live models.",
      });
    } catch (e) {
      setFeedback({ tone: "error", text: e instanceof ApiError ? e.message : "Could not load models." });
    } finally {
      setBusy(null);
    }
  }

  async function save() {
    setBusy("save");
    setFeedback(null);
    const submitted = apiKey;
    setApiKey(""); // never keep the key in UI state after submit
    try {
      const res = await api<LLMConfigStatus>("/api/session/llm-config", {
        method: "POST",
        json: { provider, model: model.trim(), api_key: submitted, test: testFirst },
      });
      setStatus(res);
      setFeedback({
        tone: "ok",
        text: testFirst ? "Key verified and saved for this session." : "Saved for this session (not tested).",
      });
      notifyLlmConfigChanged();
    } catch (e) {
      setFeedback({ tone: "error", text: e instanceof ApiError ? e.message : "Could not save the configuration." });
    } finally {
      setBusy(null);
    }
  }

  async function testSubmitted() {
    setBusy("test");
    setFeedback(null);
    const submitted = apiKey;
    try {
      const body = submitted ? { provider, model: model.trim(), api_key: submitted } : undefined;
      const res = await api<LLMTestResult>("/api/session/llm-config/test", { method: "POST", json: body });
      setFeedback({ tone: "ok", text: `${res.provider} · ${res.model} responded in ${res.latency_ms} ms.` });
    } catch (e) {
      setFeedback({ tone: "error", text: e instanceof ApiError ? e.message : "Test failed." });
    } finally {
      setBusy(null);
    }
  }

  async function clear() {
    setBusy("clear");
    setFeedback(null);
    setApiKey("");
    try {
      await api<void>("/api/session/llm-config", { method: "DELETE" });
      await refresh();
      setFeedback({ tone: "ok", text: "Your key was removed from this session." });
      notifyLlmConfigChanged();
    } catch (e) {
      setFeedback({ tone: "error", text: e instanceof ApiError ? e.message : "Could not clear the configuration." });
    } finally {
      setBusy(null);
    }
  }

  const canSave = Boolean(provider && model.trim() && apiKey.length >= 8) && busy === null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <KeyRound className="size-4 text-primary" /> LLM settings
          </DialogTitle>
          <DialogDescription>
            Research and Q&amp;A use the app&apos;s default model, or your own key for this session.
          </DialogDescription>
        </DialogHeader>

        <div className="rounded-md border bg-subtle px-3 py-2 text-sm" data-testid="llm-current">
          <div className="text-xs text-muted-foreground">Currently using</div>
          <div className="font-medium">{describeConfig(status)}</div>
          {status?.source === "session" && status.expires_at && (
            <div className="text-xs text-muted-foreground">Expires {formatDateTime(status.expires_at)}</div>
          )}
          {status?.source === "expired" && (
            <div className="mt-1 text-xs text-amber-300">
              Re-enter your key, or clear it to switch to the app default
              {status.default.available ? "" : " (none is configured on this server)"}.
            </div>
          )}
          {status?.source === "none" && (
            <div className="mt-1 text-xs text-muted-foreground">
              Seed guides work without a model. Live research and Q&amp;A need a key.
            </div>
          )}
        </div>

        <div className="grid gap-3">
          <div className="grid gap-1.5">
            <Label htmlFor={ids.provider}>Provider</Label>
            <Select value={provider} onValueChange={changeProvider}>
              <SelectTrigger id={ids.provider} aria-label="Provider" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(providers?.providers ?? []).map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {selected && <p className="text-xs text-muted-foreground">Calls go through the {selected.sdk}.</p>}
          </div>

          <div className="grid gap-1.5">
            <div className="flex items-center justify-between">
              <Label htmlFor={ids.model}>Model ID</Label>
              <button
                type="button"
                className="text-xs text-primary hover:underline disabled:opacity-50"
                onClick={loadModels}
                disabled={busy !== null}
              >
                {busy === "models" ? "Loading…" : "Load available models"}
              </button>
            </div>
            <Input
              id={ids.model}
              list={ids.models}
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="e.g. anthropic/claude-sonnet-5.5"
              autoComplete="off"
              spellCheck={false}
              className="font-mono text-xs"
            />
            <datalist id={ids.models} data-testid="model-suggestions">
              {suggestions.slice(0, 200).map((m) => (
                <option key={m} value={m} />
              ))}
            </datalist>
          </div>

          <div className="grid gap-1.5">
            <Label htmlFor={ids.key}>API key</Label>
            <Input
              id={ids.key}
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={selected?.key_hint ?? "Paste your key"}
              autoComplete="off"
              spellCheck={false}
              className="font-mono text-xs"
            />
          </div>

          <div className="flex items-center gap-2">
            <Checkbox id={ids.test} checked={testFirst} onCheckedChange={(v) => setTestFirst(v === true)} />
            <Label htmlFor={ids.test} className="text-sm font-normal">
              Test the key before saving
            </Label>
          </div>
        </div>

        {feedback && (
          <p
            role={feedback.tone === "error" ? "alert" : "status"}
            className={feedback.tone === "error" ? "text-sm text-rose-300" : "flex items-center gap-1.5 text-sm text-emerald-300"}
          >
            {feedback.tone === "ok" && <CheckCircle2 className="size-4" />}
            {feedback.text}
          </p>
        )}

        <div className="flex gap-2 rounded-md border border-dashed px-3 py-2 text-xs text-muted-foreground">
          <ShieldCheck className="mt-0.5 size-3.5 shrink-0" />
          <span>
            Your key is sent once over the same-origin API, kept only in the server&apos;s memory for this session
            (60 min), and never stored in a database, your browser, cookies, or URLs. A server restart clears it.
            If your key fails, we show the error; we never fall back to the app&apos;s key.
          </span>
        </div>

        <DialogFooter className="gap-2 sm:justify-between">
          <Button
            variant="ghost"
            onClick={clear}
            disabled={busy !== null || status?.source === "none" || status?.source === "default"}
          >
            {busy === "clear" ? <Loader2 className="animate-spin" /> : <Trash2 />}
            Clear my key
          </Button>
          <div className="flex gap-2">
            <Button variant="outline" onClick={testSubmitted} disabled={busy !== null}>
              {busy === "test" && <Loader2 className="animate-spin" />}
              Test
            </Button>
            <Button onClick={save} disabled={!canSave}>
              {busy === "save" && <Loader2 className="animate-spin" />}
              Save for this session
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
