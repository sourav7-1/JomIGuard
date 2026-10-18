import React, { Suspense } from "react";
import { CaseDetailClient } from "./CaseDetailClient";
import { Spinner } from "@/components/ui/Spinner";

async function CasePageContent({ params, searchParams }: { params: Promise<{ id: string }>; searchParams: Promise<{ source?: string; field?: string }> }) {
  const { id } = await params;
  const { source, field } = await searchParams;
  return <CaseDetailClient landId={id} source={source} field={field} />;
}

export default function CaseDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ source?: string; field?: string }>;
}) {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center min-h-[400px]">
          <Spinner size="lg" />
        </div>
      }
    >
      <CasePageContent params={params} searchParams={searchParams} />
    </Suspense>
  );
}
