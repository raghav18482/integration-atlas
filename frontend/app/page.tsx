import Link from "next/link";
import { BadgeCheck, Clock, ListChecks, ShieldAlert } from "lucide-react";

import { DiscoveryForm } from "@/components/discovery-form";
import { SeedCards } from "@/components/seed-cards";

const VALUE_PROPS = [
  {
    icon: BadgeCheck,
    title: "Evidence-backed setup",
    body: "Every requirement links to the page it came from, with the quote we matched. Unsupported claims are labelled as inferred or unknown.",
  },
  {
    icon: Clock,
    title: "Active effort vs. external waiting",
    body: "Hands-on hours are estimated separately from provider review queues, which are only shown when the provider documents them.",
  },
  {
    icon: ShieldAlert,
    title: "Approval and launch requirements",
    body: "Registration, user consent, admin consent, verification, and marketplace review are kept distinct, with what triggers each.",
  },
  {
    icon: ListChecks,
    title: "Actionable checklist",
    body: "Ordered steps with owners, dependencies, and what an agent can do for you versus where you must take over.",
  },
];

export default function Home() {
  return (
    <div className="mx-auto max-w-[1100px] px-4 py-12 lg:px-6 lg:py-16">
      <section className="mx-auto max-w-2xl text-center">
        <p className="mb-3 text-xs font-medium uppercase tracking-[0.18em] text-primary">Integration Atlas</p>
        <h1 className="text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
          Know the integration work before you build it.
        </h1>
        <p className="mt-3 text-pretty text-muted-foreground">
          Research authentication, permissions, verification requirements, and production launch blockers before you
          start coding.
        </p>
      </section>

      <section className="mx-auto mt-8 max-w-2xl">
        <DiscoveryForm />
      </section>

      <section className="mt-14" aria-labelledby="seed-heading">
        <div className="mb-3 flex items-end justify-between">
          <div>
            <h2 id="seed-heading" className="text-sm font-semibold">Curated guides</h2>
            <p className="text-xs text-muted-foreground">
              Three providers with very different setup paths. Seed content, checked by hand against official docs.
            </p>
          </div>
          <Link href="/guides" className="text-xs text-primary hover:underline">
            All saved guides →
          </Link>
        </div>
        <SeedCards />
      </section>

      <section className="mt-14 grid gap-px overflow-hidden rounded-xl border bg-border sm:grid-cols-2 lg:grid-cols-4">
        {VALUE_PROPS.map(({ icon: Icon, title, body }) => (
          <div key={title} className="bg-card p-4">
            <Icon className="mb-2 size-4 text-primary" />
            <h3 className="text-sm font-medium">{title}</h3>
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{body}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
