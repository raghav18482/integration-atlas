import type { Metadata } from "next";

import { ClaimStatusBadge } from "@/components/status-badges";
import { CLAIM_STATUS_HELP } from "@/lib/format";
import type { ClaimStatus } from "@/types";

export const metadata: Metadata = { title: "How it works" };

const STAGES = [
  ["Identify the provider", "Search results and any URL you submit are shown to the model, which picks the provider and its official domains. Domains that never appeared in the results are discarded."],
  ["Find documentation", "Targeted searches cover registration and authorization, scopes, and review/verification/distribution. Official domains are searched first; other sites are labelled secondary."],
  ["Retrieve pages", "Up to 12 pages are fetched through an SSRF-safe fetcher (public addresses only, every redirect re-checked, size and time limits). Failures are recorded, not hidden."],
  ["Extract claims", "For each topic the model proposes facts, each with a verbatim quote from one source. Page text is passed as untrusted data, never as instructions."],
  ["Check the evidence", "Code, not the model, decides each claim's status. The quote must appear in the cited page (punctuation-insensitive; numbers and wording must match). Quotes found in two retrieved pages are cross-checked."],
  ["Probe OAuth metadata", "We request standard discovery documents (OpenID Connect / RFC 8414) on official hosts. A valid document is the only thing we label “Tested”."],
  ["Draft and validate", "The model drafts the guide from the checked claims. The schema is validated, references must exist, and approval or waiting-time conclusions without documented support are downgraded to unclear/unknown."],
] as const;

const STATUSES: ClaimStatus[] = ["tested", "cross_checked", "officially_documented", "inferred", "estimated", "unknown"];

export default function HowItWorks() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-10 lg:px-6">
      <h1 className="text-2xl font-semibold tracking-tight">How it works</h1>
      <p className="mt-2 text-muted-foreground">
        Integration Atlas turns scattered provider documentation into a setup guide you can follow and share, and is
        explicit about which parts are evidence and which are judgment.
      </p>

      <section className="mt-8">
        <h2 className="text-lg font-semibold">Why an OAuth app is the bottleneck</h2>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          When your agent connects to a user&apos;s account, the user grants access to an <em>OAuth app</em>: a
          registration with the provider that holds your client ID, secret, redirect URLs, and requested scopes.
          Integration platforms sometimes offer a managed OAuth app you can borrow. Otherwise you register your own,
          and broad scopes or public distribution can trigger provider verification or marketplace review that takes
          days to weeks. That wait, not the code, usually decides your launch date.
        </p>
      </section>

      <section className="mt-8">
        <h2 className="text-lg font-semibold">The research pipeline</h2>
        <ol className="mt-3 grid gap-3">
          {STAGES.map(([title, body], i) => (
            <li key={title} className="flex gap-3 rounded-lg border bg-card p-3">
              <span className="font-mono text-xs text-muted-foreground">{i + 1}</span>
              <div>
                <div className="text-sm font-medium">{title}</div>
                <p className="mt-0.5 text-sm text-muted-foreground">{body}</p>
              </div>
            </li>
          ))}
        </ol>
        <p className="mt-3 text-xs text-muted-foreground">
          Every stage writes a real progress event; the research screen shows them as they happen. Nothing is
          simulated.
        </p>
      </section>

      <section className="mt-8">
        <h2 className="text-lg font-semibold">Evidence labels</h2>
        <dl className="mt-3 grid gap-2">
          {STATUSES.map((s) => (
            <div key={s} className="flex items-start gap-3">
              <dt className="w-28 shrink-0">
                <ClaimStatusBadge status={s} />
              </dt>
              <dd className="text-sm text-muted-foreground">{CLAIM_STATUS_HELP[s]}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="mt-8">
        <h2 className="text-lg font-semibold">Effort, waiting, and approval</h2>
        <ul className="mt-2 list-disc pl-5 text-sm leading-relaxed text-muted-foreground">
          <li>Active effort is your hands-on time, summed from per-step estimates. It is always labelled an estimate.</li>
          <li>External waiting (reviews, verification queues) is shown only when the provider documents a duration. Otherwise it is “Unknown”, with what triggers it.</li>
          <li>There is no approval-probability score. The progress bars show your checklist and the share of evidence-backed claims, nothing more.</li>
        </ul>
      </section>

      <section className="mt-8">
        <h2 className="text-lg font-semibold">Your API key</h2>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          You can use the app&apos;s default model or bring your own Anthropic, OpenAI, or OpenRouter key for this
          session. The key is held only in the server&apos;s memory for up to 60 minutes, bound to your browser&apos;s
          signed session, never written to the database, logs, cookies, or browser storage, and never returned to the
          page. If your key fails, you see the error; the app never silently switches to its own key.
        </p>
      </section>

      <section className="mt-8">
        <h2 className="text-lg font-semibold">Limitations</h2>
        <ul className="mt-2 list-disc pl-5 text-sm leading-relaxed text-muted-foreground">
          <li>Retrieved documentation is not a working integration. We don&apos;t create provider accounts or submit apps for review.</li>
          <li>Pages that need JavaScript to render may only be available as search snippets, which are never treated as documented evidence.</li>
          <li>Providers change their docs; check the “last checked” date and re-run research before committing to a launch date.</li>
        </ul>
      </section>
    </div>
  );
}
