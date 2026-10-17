import React, { Suspense } from "react";
import { CaseDetailClient } from "./CaseDetailClient";
import { Spinner } from "@/components/ui/Spinner";

async function CasePageContent({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <CaseDetailClient landId={id} />;
}

export default function CaseDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center min-h-[400px]">
          <Spinner size="lg" />
        </div>
      }
    >
      <CasePageContent params={params} />
    </Suspense>
  );
}
