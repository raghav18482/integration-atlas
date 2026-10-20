import { vi } from "vitest";

type Handler = (url: string, init: RequestInit) => { status?: number; body?: unknown } | undefined;

export type RecordedCall = { url: string; method: string; headers: Record<string, string>; body: unknown };

/** Installs a fetch mock that routes by URL and records every call. */
export function mockFetch(handler: Handler) {
  const calls: RecordedCall[] = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const url = typeof input === "string" ? input : input.toString();
    const headers = (init.headers ?? {}) as Record<string, string>;
    calls.push({
      url,
      method: init.method ?? "GET",
      headers,
      body: typeof init.body === "string" ? JSON.parse(init.body) : undefined,
    });
    const res = handler(url, init) ?? { status: 404, body: { error: { code: "not_found", message: "Not found" } } };
    const status = res.status ?? 200;
    return new Response(status === 204 ? null : JSON.stringify(res.body ?? {}), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return { calls, fetchMock };
}

export const PROVIDERS = {
  providers: [
    { id: "anthropic", label: "Anthropic", sdk: "anthropic Python SDK", key_hint: "sk-ant-…", suggested_models: ["claude-sonnet-5-5"] },
    { id: "openai", label: "OpenAI", sdk: "openai Python SDK", key_hint: "sk-…", suggested_models: ["gpt-5.5"] },
    {
      id: "openrouter",
      label: "OpenRouter",
      sdk: "openai Python SDK (OpenRouter base URL)",
      key_hint: "sk-or-…",
      suggested_models: ["anthropic/claude-sonnet-5.5", "nvidia/nemotron-3-super-120b-a12b"],
    },
  ],
  default: { available: false, provider: null, model: null },
  search_configured: false,
};

export const NO_CONFIG = { source: "none", default: { available: false } };
