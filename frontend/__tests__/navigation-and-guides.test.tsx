import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SeedCards } from "@/components/seed-cards";
import { NAV, SiteHeader } from "@/components/site-header";
import { TooltipProvider } from "@/components/ui/tooltip";

import { mockFetch, NO_CONFIG, PROVIDERS } from "./helpers";

const SEEDS = {
  items: [
    {
      slug: "slack",
      provider_name: "Slack",
      authentication_model: "oauth2",
      intended_use_case: "An AI agent that reads channel history",
      integration_context: "multi_tenant_saas",
      origin: "seed",
      research_status: "seed_curated",
      generated_at: "2026-10-20T09:00:00Z",
      last_checked_at: "2026-10-20T09:00:00Z",
      evidence_coverage: 0.958,
      claims_total: 24,
      sources_total: 7,
      approval_status: "conditional",
    },
  ],
  total: 1,
  limit: 6,
  offset: 0,
};

describe("navigation", () => {
  it("links to every main section and the LLM settings", async () => {
    mockFetch((url) => (url === "/api/session/llm-config" ? { body: NO_CONFIG } : url === "/api/llm/providers" ? { body: PROVIDERS } : undefined));
    render(
      <TooltipProvider>
        <SiteHeader />
      </TooltipProvider>,
    );
    for (const item of NAV) {
      const links = screen.getAllByRole("link", { name: item.label });
      expect(links[0]).toHaveAttribute("href", item.href);
    }
    expect(screen.getByRole("link", { name: /integration atlas/i })).toHaveAttribute("href", "/");
    expect(await screen.findByRole("button", { name: "LLM settings" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "LLM settings" })).toHaveTextContent("No model configured"));
  });
});

describe("seed cards", () => {
  it("link to stable guide URLs and are labelled as seed content", async () => {
    mockFetch((url) => (url.startsWith("/api/guides") ? { body: SEEDS } : undefined));
    render(<SeedCards />);
    const card = await screen.findByRole("link", { name: /slack/i });
    expect(card).toHaveAttribute("href", "/guides/slack");
    expect(card).toHaveTextContent("Seed guide");
    expect(card).toHaveTextContent("Checked Oct 20, 2026");
    expect(card).not.toHaveTextContent(/just researched|researching/i);
  });

  it("shows loading then an error state", async () => {
    mockFetch(() => ({ status: 500, body: { error: { code: "internal_error", message: "An unexpected error occurred." } } }));
    render(<SeedCards />);
    expect(document.querySelector('[aria-busy="true"]')).not.toBeNull();
    expect(await screen.findByRole("alert")).toHaveTextContent("An unexpected error occurred.");
  });
});
