import type { Metadata } from "next";
import { Suspense } from "react";

import { GuideWorkspace } from "@/components/guide/guide-workspace";
import { Skeleton } from "@/components/ui/skeleton";

export const metadata: Metadata = { title: "Integration guide" };

async function Loader({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return <GuideWorkspace slug={slug} />;
}

export default function GuidePage({ params }: PageProps<"/guides/[slug]">) {
  return (
    <div className="mx-auto max-w-[1400px] px-4 py-8 lg:px-6">
      <Suspense fallback={<Skeleton className="h-[600px]" />}>
        <Loader params={params} />
      </Suspense>
    </div>
  );
}
