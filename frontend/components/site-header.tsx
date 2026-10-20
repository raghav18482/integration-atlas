"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { Compass, KeyRound } from "lucide-react";

import { LlmSettingsDialog, describeConfig } from "@/components/llm-settings-dialog";
import { Button } from "@/components/ui/button";
import { api, LLM_CONFIG_CHANGED, OPEN_LLM_SETTINGS } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { LLMConfigStatus } from "@/types";

export const NAV = [
  { href: "/", label: "Explore" },
  { href: "/guides", label: "Saved Guides" },
  { href: "/how-it-works", label: "How It Works" },
] as const;

const linkClass =
  "rounded-md px-2.5 py-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground";

function NavLinksStatic() {
  return (
    <>
      {NAV.map((item) => (
        <Link key={item.href} href={item.href} className={linkClass}>
          {item.label}
        </Link>
      ))}
    </>
  );
}

// usePathname is request-time URL data, so it lives behind its own Suspense boundary.
function NavLinksActive() {
  const pathname = usePathname();
  return (
    <>
      {NAV.map((item) => {
        const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={cn(linkClass, active && "bg-muted text-foreground")}
          >
            {item.label}
          </Link>
        );
      })}
    </>
  );
}

export function SiteHeader() {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<LLMConfigStatus | null>(null);

  const load = useCallback(() => {
    api<LLMConfigStatus>("/api/session/llm-config")
      .then(setStatus)
      .catch(() => setStatus(null));
  }, []);

  useEffect(() => {
    load();
    const onChange = () => load();
    const onOpen = () => setOpen(true);
    window.addEventListener(LLM_CONFIG_CHANGED, onChange);
    window.addEventListener(OPEN_LLM_SETTINGS, onOpen);
    return () => {
      window.removeEventListener(LLM_CONFIG_CHANGED, onChange);
      window.removeEventListener(OPEN_LLM_SETTINGS, onOpen);
    };
  }, [load]);

  const dot =
    status?.source === "session" || status?.source === "default"
      ? "bg-emerald-400"
      : status?.source === "expired"
        ? "bg-amber-400"
        : "bg-zinc-500";

  return (
    <header className="sticky top-0 z-40 border-b bg-background/85 backdrop-blur supports-[backdrop-filter]:bg-background/70">
      <div className="mx-auto flex h-14 max-w-[1400px] items-center gap-6 px-4 lg:px-6">
        <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <span className="grid size-6 place-items-center rounded-md bg-primary/15 text-primary">
            <Compass className="size-4" />
          </span>
          Integration Atlas
        </Link>
        <nav aria-label="Main" className="hidden items-center gap-1 text-sm md:flex">
          <Suspense fallback={<NavLinksStatic />}>
            <NavLinksActive />
          </Suspense>
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => setOpen(true)} aria-label="LLM settings">
            <span className={cn("size-1.5 rounded-full", dot)} aria-hidden />
            <KeyRound className="text-muted-foreground" />
            <span className="hidden max-w-[260px] truncate sm:inline">{describeConfig(status)}</span>
            <span className="sm:hidden">LLM</span>
          </Button>
        </div>
      </div>
      <nav aria-label="Main mobile" className="flex gap-1 border-t px-4 py-1.5 text-sm md:hidden">
        {NAV.map((item) => (
          <Link key={item.href} href={item.href} className="rounded-md px-2 py-1 text-muted-foreground hover:text-foreground">
            {item.label}
          </Link>
        ))}
      </nav>
      <LlmSettingsDialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) load(); }} />
    </header>
  );
}
