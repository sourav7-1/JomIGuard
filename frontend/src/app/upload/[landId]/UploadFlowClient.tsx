"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import {
  DocumentDropZone,
  type DropZoneHandle,
  type PendingUpload,
} from "@/components/upload/DocumentDropZone";
import { DocumentProgressCard } from "@/components/upload/DocumentProgressCard";
import { RecommendedDocList } from "@/components/upload/RecommendedDocList";
import { SampleSetCard } from "@/components/upload/SampleSetCard";
import { api, type DocumentStatusOut, type LandOut } from "@/lib/api";
import { bnDigits } from "@/lib/digits";
import { useLang, useStrings } from "@/lib/lang";

export interface UploadFlowClientProps {
  landId: string;
}

export function UploadFlowClient({ landId }: UploadFlowClientProps) {
  const strings = useStrings();
  const en = useLang() === "en";
  const t = (b: string, e: string) => (en ? e : b);
  const router = useRouter();

  const [land, setLand] = useState<LandOut | null>(null);
  const [documents, setDocuments] = useState<DocumentStatusOut[]>([]);
  const [pendingUploads, setPendingUploads] = useState<Record<string, PendingUpload>>({});
  const [uploadPercents, setUploadPercents] = useState<Record<string, number>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isAssessing, setIsAssessing] = useState(false);
  const [assessError, setAssessError] = useState<string | null>(null);
  const dropZone = useRef<DropZoneHandle>(null);

  // 1. Load land details and existing documents on mount (so page survives refresh)
  useEffect(() => {
    let isMounted = true;

    async function loadData() {
      try {
        const [landData, docsData] = await Promise.all([
          api.getLand(landId).catch(() => null),
          api.getLandDocuments(landId).catch(() => []),
        ]);

        if (isMounted) {
          if (landData) setLand(landData);
          if (docsData) setDocuments(docsData);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadData();

    return () => {
      isMounted = false;
    };
  }, [landId]);

  // Handlers for upload lifecycle
  const handleUploadStart = useCallback((pending: PendingUpload) => {
    setPendingUploads((prev) => ({ ...prev, [pending.id]: pending }));
    setUploadPercents((prev) => ({ ...prev, [pending.id]: 0 }));
  }, []);

  const handleUploadProgress = useCallback((tempId: string, percent: number) => {
    setUploadPercents((prev) => ({ ...prev, [tempId]: percent }));
    setPendingUploads((prev) => prev[tempId] ? { ...prev, [tempId]: { ...prev[tempId], status: "uploading", progress: percent } } : prev);
  }, []);

  const handleUploadError = useCallback((tempId: string, error: string) => {
    setPendingUploads((prev) => {
      const copy = { ...prev };
      if (copy[tempId]) {
        copy[tempId] = { ...copy[tempId], status: "error", error };
      }
      return copy;
    });
  }, []);

  const handleUploadSuccess = useCallback((newDoc: DocumentStatusOut, uploadId: string) => {
    // Add to documents list or update if exists
    setDocuments((prev) => {
      const existingIdx = prev.findIndex((d) => d.id === newDoc.id);
      if (existingIdx >= 0) {
        const updated = [...prev];
        updated[existingIdx] = newDoc;
        return updated;
      }
      return [...prev, newDoc];
    });

    // Remove from pending uploads
    setPendingUploads((prev) => {
      const copy = { ...prev };
      delete copy[uploadId];
      return copy;
    });
    setUploadPercents((prev) => { const copy = { ...prev }; delete copy[uploadId]; return copy; });
  }, []);

  // Handler for document status updates during polling
  const handleDocumentUpdate = useCallback((updated: DocumentStatusOut) => {
    setDocuments((prev) =>
      prev.map((doc) => (doc.id === updated.id ? updated : doc))
    );
  }, []);

  // Handler for removing a document from list
  const handleDocumentRemove = useCallback(async (docId: string) => {
    try {
      await api.detachDocument(docId);
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
    } catch {
      setAssessError(strings.error.defaultMessage);
    }
  }, [strings.error.defaultMessage]);

  // Handler for "যাচাই করুন" (Assess)
  const handleAssess = async () => {
    setAssessError(null);
    setIsAssessing(true);
    try {
      await api.assessLand(landId);
      router.push(`/cases/${landId}`);
    } catch (err: unknown) {
      setAssessError(err instanceof Error ? err.message : strings.uploadFlow.errAssess);
      setIsAssessing(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center p-16 space-y-3">
        <Spinner size="lg" />
        <p className="text-sm text-muted">{strings.labels.loading}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto py-4">
      {/* Top Banner: Step & Land Info */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-line pb-4">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-accent-soft text-accent text-xs font-semibold">
            <span>{t("ধাপ ২", "Step 2")}</span> • {strings.uploadFlow.step2Title}
          </div>
          <h1 className="text-xl md:text-2xl font-bold font-heading text-ink">
            {strings.uploadFlow.step2Title}
          </h1>
          {land && (
            <p className="text-xs md:text-sm text-muted flex flex-wrap items-center gap-2">
              <span className="font-semibold text-ink">
                {strings.uploadFlow.landInfoPrefix}
              </span>
              <span>{t("মৌজা", "Mouza")}: {land.mouza}</span>
              {land.dag_no && <span>• {t("দাগ", "Dag")}: {en ? land.dag_no : bnDigits(land.dag_no)}</span>}
              {land.khatian_no && <span>• {t("খতিয়ান", "Khatian")}: {en ? land.khatian_no : bnDigits(land.khatian_no)}</span>}
              {land.upazila && <span>• {t("উপজেলা", "Upazila")}: {land.upazila}</span>}
            </p>
          )}
        </div>

        <Link
          href="/upload"
          className="min-h-[44px] px-3.5 py-2 text-xs font-medium rounded-lg border border-line bg-surface text-ink hover:bg-bg transition-colors flex items-center justify-center self-start sm:self-center focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          ← {strings.buttons.newCheck}
        </Link>
      </div>

      {/* Main 2-column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Left Column (2 cols on lg): Drop zone & Document Progress Cards */}
        <div className="lg:col-span-2 space-y-6">
          <SampleSetCard landId={landId} dropZone={dropZone} hasDocuments={documents.length > 0} />

          <DocumentDropZone
            ref={dropZone}
            landId={landId}
            onUploadStart={handleUploadStart}
            onUploadProgress={handleUploadProgress}
            onUploadError={handleUploadError}
            onUploadSuccess={handleUploadSuccess}
          />

          {/* Documents Section */}
          <div className="space-y-3">
            <h2 className="text-base font-bold font-heading text-ink">
              {t("কাগজপত্র", "Papers")} ({en ? documents.length : bnDigits(documents.length)})
            </h2>

            {documents.length === 0 && Object.keys(pendingUploads).length === 0 ? (
              <Card className="p-8 text-center border-dashed bg-surface/50">
                <p className="text-sm text-muted">
                  {strings.uploadFlow.noDocsYet}
                </p>
                <p className="mt-2 text-sm">
                  {t("হাতে কাগজ নেই?", "No papers at hand?")}{" "}
                  <a href="#samples" className="font-semibold text-accent underline underline-offset-4 hover:no-underline">
                    {t("উপরের নমুনা কাগজ দিয়ে চেষ্টা করুন", "Try the sample documents above")}
                  </a>
                </p>
              </Card>
            ) : (
              <div className="space-y-3">
                {Object.values(pendingUploads).map((upload) => <Card key={upload.id} className="p-4"><div className="flex items-center justify-between gap-3"><div className="min-w-0"><p className="truncate text-sm font-semibold text-ink">{upload.name}</p><p className="text-xs text-muted">{upload.status === "error" ? upload.error : upload.status === "optimizing" ? t("ফাইল প্রস্তুত হচ্ছে", "Preparing file") : t("আপলোড হচ্ছে", "Uploading")}</p></div><button type="button" onClick={() => { setPendingUploads((prev) => { const copy = { ...prev }; delete copy[upload.id]; return copy; }); setUploadPercents((prev) => { const copy = { ...prev }; delete copy[upload.id]; return copy; }); }} className="min-h-11 min-w-11 rounded-lg text-sm text-muted hover:bg-bg" aria-label={`${upload.name} ${t("তালিকা থেকে সরান", "remove from list")}`}>×</button></div>{upload.status !== "error" && <div className="mt-3 h-2 overflow-hidden rounded-full bg-line" role="progressbar" aria-label={`${upload.name} ${t("আপলোডের অগ্রগতি", "upload progress")}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={upload.progress}><div className="h-full bg-accent transition-[width]" style={{ width: `${upload.progress}%` }} /></div>}</Card>)}
                {/* Uploaded Documents */}
                {documents.map((doc) => (
                  <DocumentProgressCard
                    key={doc.id}
                    document={doc}
                    uploadPercent={uploadPercents[doc.id]}
                    onUpdate={handleDocumentUpdate}
                    onRemove={handleDocumentRemove}
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Recommended Document List Sidebar & Assess Action */}
        <div className="lg:col-span-1 sticky top-20">
          <RecommendedDocList
            documents={documents}
            onAssess={handleAssess}
            isAssessing={isAssessing}
            assessError={assessError}
          />
        </div>
      </div>
    </div>
  );
}
