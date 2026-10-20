// Same-origin API client. Next.js rewrites /api/* to the FastAPI backend, so the
// backend's HttpOnly session cookies work without CORS. State-changing requests
// carry the CSRF header the backend requires.

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

type Options = {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  json?: unknown;
  signal?: AbortSignal;
};

export async function api<T>(path: string, { method = "GET", json, signal }: Options = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (method !== "GET") headers["X-Atlas-CSRF"] = "1";
  if (json !== undefined) headers["Content-Type"] = "application/json";

  let response: Response;
  try {
    response = await fetch(path, {
      method,
      headers,
      body: json === undefined ? undefined : JSON.stringify(json),
      credentials: "same-origin",
      cache: "no-store",
      signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new ApiError(0, "network_error", "Could not reach the Integration Atlas API. Is the backend running?");
  }

  if (response.status === 204) return undefined as T;

  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  if (!response.ok) {
    const error = (body as { error?: { code?: string; message?: string } } | null)?.error;
    throw new ApiError(
      response.status,
      error?.code ?? "http_error",
      error?.message ?? `Request failed (HTTP ${response.status}).`,
    );
  }
  return body as T;
}

export const LLM_CONFIG_CHANGED = "atlas:llm-config-changed";

export function notifyLlmConfigChanged() {
  window.dispatchEvent(new Event(LLM_CONFIG_CHANGED));
}

export const OPEN_LLM_SETTINGS = "atlas:open-llm-settings";

export function openLlmSettings() {
  window.dispatchEvent(new Event(OPEN_LLM_SETTINGS));
}
