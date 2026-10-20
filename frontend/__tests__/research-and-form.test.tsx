import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { DiscoveryForm } from "@/components/discovery-form";
import { ResearchWorkspace } from "@/components/research-workspace";

import { mockFetch } from "./helpers";

const STAGES = [
  { key: "resolve", label: "Identifying provider" },
  { key: "discover", label: "Finding authentication documentation" },
  { key: "retrieve", label: "Retrieving documentation pages" },
];

function run(overrides: Record<string, unknown>) {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    status: "running",
    stage: "discover",
    stages: STAGES,
    query: "Notion",
    submitted_url: null,
    intended_use_case: "",
    integration_context: "multi_tenant_saas",
    provider_name: "Notion",
    refresh_of_slug: null,
    events: [
      { ts: "2026-10-20T10:00:00Z", stage: "resolve", label: "Identifying provider", status: "completed", message: "Identified Notion." },
      { ts: "2026-10-20T10:00:01Z", stage: "discover", label: "Finding", status: "started", message: "Searching…" },
    ],
    sources: [
      { id: "S1", url: "https://developers.notion.com/docs/authorization", title: "Authorization", domain: "developers.notion.com", official: true, status: "retrieved" },
      { id: "S2", url: "https://developers.notion.com/x", title: "JS page", domain: "developers.notion.com", official: true, status: "failed", error: "HTTP 403" },
    ],
    guide_slug: null,
    error_code: null,
    error_message: null,
    llm: { provider: "openrouter", model: "openai/gpt-5.5", source: "default" },
    created_at: "2026-10-20T10:00:00Z",
    finished_at: null,
    ...overrides,
  };
}

describe("research workspace", () => {
  it("renders real stage states and source counts while running", async () => {
    mockFetch(() => ({ body: run({}) }));
    render(<ResearchWorkspace runId="11111111-1111-1111-1111-111111111111" />);
    expect(await screen.findByText("Identified Notion.")).toBeInTheDocument();
    expect(document.querySelector('[data-stage="resolve"]')).toHaveAttribute("data-state", "done");
    expect(document.querySelector('[data-stage="discover"]')).toHaveAttribute("data-state", "active");
    expect(document.querySelector('[data-stage="retrieve"]')).toHaveAttribute("data-state", "pending");
    expect(screen.getByText(/2 discovered · 1 retrieved · 0 snippet only · 1 failed/)).toBeInTheDocument();
    expect(screen.getByText("HTTP 403")).toBeInTheDocument();
  });

  it("links to the guide on success", async () => {
    mockFetch(() => ({ body: run({ status: "completed", guide_slug: "notion-abc123", finished_at: "2026-10-20T10:02:00Z" }) }));
    render(<ResearchWorkspace runId="11111111-1111-1111-1111-111111111111" />);
    expect(await screen.findByRole("link", { name: /open guide/i })).toHaveAttribute("href", "/guides/notion-abc123");
  });

  it("shows failures honestly with retry and settings actions", async () => {
    mockFetch(() => ({
      body: run({
        status: "failed",
        error_code: "llm_invalid_credentials",
        error_message: "Anthropic rejected the API key. Check the key and try again.",
        events: [{ ts: "2026-10-20T10:00:00Z", stage: "resolve", label: "x", status: "failed", message: "Anthropic rejected the API key." }],
        sources: [],
      }),
    }));
    render(<ResearchWorkspace runId="11111111-1111-1111-1111-111111111111" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Research failed.");
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /llm settings/i })).toBeInTheDocument();
    expect(document.querySelector('[data-stage="resolve"]')).toHaveAttribute("data-state", "failed");
  });
});

describe("discovery form", () => {
  it("submits the request and surfaces configuration errors", async () => {
    const { calls } = mockFetch((url) =>
      url === "/api/research"
        ? { status: 503, body: { error: { code: "llm_not_configured", message: "No language model is configured." } } }
        : { body: { items: [], total: 0, limit: 3, offset: 0 } },
    );
    render(<DiscoveryForm />);
    await userEvent.type(screen.getByLabelText(/application name or documentation url/i), "Notion");
    await userEvent.click(screen.getByRole("radio", { name: /internal company tool/i }));
    await userEvent.click(screen.getByRole("button", { name: /generate integration guide/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("No language model is configured.");
    expect(screen.getByRole("button", { name: /open llm settings/i })).toBeInTheDocument();
    const post = calls.find((c) => c.method === "POST");
    expect(post?.body).toMatchObject({ query: "Notion", integration_context: "internal" });
    expect(post?.headers["X-Atlas-CSRF"]).toBe("1");
  });
});
