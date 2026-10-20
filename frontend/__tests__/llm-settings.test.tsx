import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { LlmSettingsDialog } from "@/components/llm-settings-dialog";

import { mockFetch, NO_CONFIG, PROVIDERS } from "./helpers";

const SECRET = "sk-ant-test-secret-1234567890";

function setup(overrides: Partial<Record<string, { status?: number; body?: unknown }>> = {}) {
  let config: unknown = NO_CONFIG;
  const { calls } = mockFetch((url, init) => {
    const method = init.method ?? "GET";
    if (url === "/api/llm/providers") return { body: PROVIDERS };
    if (url === "/api/session/llm-config" && method === "GET") return { body: config };
    if (url === "/api/session/llm-config" && method === "POST") {
      if (overrides.save) return overrides.save;
      config = {
        source: "session",
        provider: "anthropic",
        provider_label: "Anthropic",
        model: "claude-sonnet-5-5",
        verified: true,
        expires_at: "2026-10-20T12:00:00Z",
        default: { available: false },
      };
      return { body: config };
    }
    if (url === "/api/session/llm-config" && method === "DELETE") {
      config = NO_CONFIG;
      return { status: 204 };
    }
    return undefined;
  });
  render(<LlmSettingsDialog open onOpenChange={() => undefined} />);
  return { calls };
}

describe("LLM settings dialog", () => {
  it("masks the API key input", async () => {
    setup();
    const key = await screen.findByLabelText("API key");
    expect(key).toHaveAttribute("type", "password");
    expect(key).toHaveAttribute("autocomplete", "off");
  });

  it("updates model suggestions when the provider changes", async () => {
    setup();
    const model = await screen.findByLabelText("Model ID");
    await waitFor(() => expect(model).toHaveValue("anthropic/claude-sonnet-5.5"));

    await userEvent.click(screen.getByRole("combobox", { name: "Provider" }));
    await userEvent.click(await screen.findByRole("option", { name: "Anthropic" }));

    expect(model).toHaveValue("claude-sonnet-5-5");
    const options = within(screen.getByTestId("model-suggestions")).getAllByRole("option", { hidden: true });
    expect(options.map((o) => o.getAttribute("value"))).toEqual(["claude-sonnet-5-5"]);
  });

  it("saves the key without keeping or displaying it", async () => {
    const { calls } = setup();
    await userEvent.click(await screen.findByRole("combobox", { name: "Provider" }));
    await userEvent.click(await screen.findByRole("option", { name: "Anthropic" }));
    const key = screen.getByLabelText("API key");
    await userEvent.type(key, SECRET);
    await userEvent.click(screen.getByRole("button", { name: /save for this session/i }));

    await screen.findByText(/verified and saved/i);
    expect(key).toHaveValue("");
    expect(document.body.textContent).not.toContain(SECRET);
    expect(screen.getByTestId("llm-current")).toHaveTextContent("Your key · Anthropic · claude-sonnet-5-5");

    const post = calls.find((c) => c.method === "POST");
    expect(post?.headers["X-Atlas-CSRF"]).toBe("1");
    expect(post?.body).toMatchObject({ provider: "anthropic", model: "claude-sonnet-5-5", api_key: SECRET, test: true });
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
    expect(document.cookie).not.toContain(SECRET);
  });

  it("shows a safe error when the key is rejected and clears the field", async () => {
    setup({
      save: { status: 400, body: { error: { code: "llm_invalid_credentials", message: "Anthropic rejected the API key." } } },
    });
    const key = await screen.findByLabelText("API key");
    await userEvent.type(key, SECRET);
    await userEvent.click(screen.getByRole("button", { name: /save for this session/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Anthropic rejected the API key.");
    expect(key).toHaveValue("");
  });

  it("clears the session configuration", async () => {
    const { calls } = setup();
    const key = await screen.findByLabelText("API key");
    await userEvent.type(key, SECRET);
    await userEvent.click(screen.getByRole("button", { name: /save for this session/i }));
    await screen.findByText(/verified and saved/i);

    await userEvent.click(screen.getByRole("button", { name: /clear my key/i }));
    await screen.findByText(/removed from this session/i);
    expect(calls.some((c) => c.method === "DELETE" && c.url === "/api/session/llm-config")).toBe(true);
    expect(screen.getByTestId("llm-current")).toHaveTextContent("No model configured");
  });
});
