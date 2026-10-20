import type { Metadata } from "next";

import { SavedGuides } from "@/components/saved-guides";

export const metadata: Metadata = { title: "Saved guides" };

export default function GuidesPage() {
  return (
    <div className="mx-auto max-w-[1200px] px-4 py-8 lg:px-6">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Saved guides</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Seed guides are curated by hand and labelled with the date they were checked. Live research guides show when
          they were generated and how much of their content is backed by retrieved sources.
        </p>
      </div>
      <SavedGuides />
    </div>
  );
}
