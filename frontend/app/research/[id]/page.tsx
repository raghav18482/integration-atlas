import type { Metadata } from "next";
import { Suspense } from "react";

import { ResearchWorkspace } from "@/components/research-workspace";
import { Skeleton } from "@/components/ui/skeleton";

export const metadata: Metadata = { title: "Research" };

async function Loader({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ResearchWorkspace runId={id} />;
}

export default function ResearchPage({ params }: PageProps<"/research/[id]">) {
  return (
    <div className="mx-auto max-w-[1200px] px-4 py-8 lg:px-6">
      <Suspense fallback={<Skeleton className="h-96" />}>
        <Loader params={params} />
      </Suspense>
    </div>
  );
}
