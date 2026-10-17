import React, { Suspense } from "react";
import { Spinner } from "@/components/ui/Spinner";
import { UploadFlowClient } from "./UploadFlowClient";
import { strings } from "@/lib/strings";

interface PageProps {
  params: Promise<{ landId: string }>;
}

async function UploadFlowPageContent({ params }: PageProps) {
  const { landId } = await params;
  return <UploadFlowClient landId={landId} />;
}

export default function UploadFlowPage({ params }: PageProps) {
  return (
    <Suspense
      fallback={
        <div className="flex flex-col items-center justify-center p-16 space-y-3">
          <Spinner size="lg" />
          <p className="text-sm text-muted">{strings.labels.loading}</p>
        </div>
      }
    >
      <UploadFlowPageContent params={params} />
    </Suspense>
  );
}
