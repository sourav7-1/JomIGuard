"use client";

import React, { useEffect, useRef, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { api, type DocumentStatusOut } from "@/lib/api";
import { strings } from "@/lib/strings";

export interface DocumentProgressCardProps {
  document: DocumentStatusOut;
  uploadPercent?: number; // 0-100 if still uploading via XHR
  onUpdate: (updated: DocumentStatusOut) => void;
  onRemove: (id: string) => void;
  className?: string;
}

const PIPELINE_STEPS = [
  { id: "queued", label: strings.uploadFlow.pipelineUpload },
  { id: "reading", label: strings.uploadFlow.pipelineReading },
  { id: "classifying", label: strings.uploadFlow.pipelineClassifying },
  { id: "extracting", label: strings.uploadFlow.pipelineExtracting },
  { id: "finished", label: strings.uploadFlow.pipelineFinished },
];

function getStepIndex(step: string | null | undefined, status: string): number {
  if (status === "done") return 4;
  switch (step) {
    case "queued":
      return 0;
    case "reading":
      return 1;
    case "classifying":
      return 2;
    case "extracting":
    case "normalizing":
      return 3;
    case "finished":
      return 4;
    default:
      return status === "uploaded" ? 0 : 1;
  }
}

function getDetectedTypeLabel(type: string | null | undefined): string {
  if (!type) return "";
  switch (type) {
    case "khatian":
      return strings.uploadFlow.recCurrentKhatian; // বর্তমান খতিয়ান
    case "deed":
      return strings.uploadFlow.docTypeDeed; // দলিল
    case "dcr":
      return strings.uploadFlow.docTypeDcr; // নামজারি-ডিসিআর
    case "heir_cert":
      return strings.uploadFlow.docTypeHeirCert; // ওয়ারিশ সনদ
    default:
      return strings.uploadFlow.docTypeOther;
  }
}

export function DocumentProgressCard({
  document: doc,
  uploadPercent,
  onUpdate,
  onRemove,
  className = "",
}: DocumentProgressCardProps) {
  const [isReprocessing, setIsReprocessing] = useState(false);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const activeRef = useRef(true);

  const isUploading = typeof uploadPercent === "number" && uploadPercent < 100;
  const isFailed = doc.status === "failed";
  const isDone = doc.status === "done";
  const isProcessing = doc.status === "processing" || doc.status === "uploaded";
  const currentStepIdx = getStepIndex(doc.current_step, doc.status);

  // Polling logic
  useEffect(() => {
    activeRef.current = true;

    // Clear existing timer
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }

    if (!isProcessing || isUploading) {
      return;
    }

    const poll = async () => {
      // Don't poll if page is hidden or component unmounted
      if (!activeRef.current || document.visibilityState === "hidden") {
        return;
      }

      try {
        const fresh = await api.getDocument(doc.id);
        if (!activeRef.current) return;
        onUpdate(fresh);

        // Schedule next poll if still processing
        if (fresh.status === "processing" || fresh.status === "uploaded") {
          const delaySec = fresh.poll_after_s || 2;
          timerRef.current = setTimeout(poll, delaySec * 1000);
        }
      } catch {
        // If poll fails, retry after default interval
        if (activeRef.current) {
          timerRef.current = setTimeout(poll, 3000);
        }
      }
    };

    const delaySec = doc.poll_after_s || 2;
    timerRef.current = setTimeout(poll, delaySec * 1000);

    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible" && activeRef.current) {
        poll();
      }
    };

    window.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      activeRef.current = false;
      if (timerRef.current) clearTimeout(timerRef.current);
      window.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [doc.id, doc.status, doc.poll_after_s, isProcessing, isUploading, onUpdate]);

  const handleReprocess = async () => {
    setIsReprocessing(true);
    try {
      const restarted = await api.reprocessDocument(doc.id);
      onUpdate({
        ...doc,
        ...restarted,
        status: "processing",
        current_step: "queued",
        error_message: null,
        is_stale: false,
      });
    } catch {
      // Ignore or let next poll handle
    } finally {
      setIsReprocessing(false);
    }
  };

  const detectedLabel = getDetectedTypeLabel(doc.detected_doc_type || doc.doc_type);

  return (
    <div
      role="region"
      aria-live="polite"
      aria-label={`${doc.original_filename} - ${doc.step_label_bn || doc.status_label_bn}`}
      className={`rounded-2xl border border-line bg-surface p-4 md:p-5 space-y-4 shadow-xs transition-colors ${className}`}
    >
      {/* Header: File Name & Badges */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-line/60 pb-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <span className="text-xl" aria-hidden="true">
            {doc.original_filename.endsWith(".pdf") ? "📑" : "🖼️"}
          </span>
          <div className="truncate">
            <h4 className="text-sm md:text-base font-bold text-ink truncate">
              {doc.original_filename}
            </h4>
            <div className="text-xs text-muted flex items-center gap-2 mt-0.5">
              <span>{doc.step_label_bn || doc.status_label_bn}</span>
              {isUploading && (
                <span className="font-mono text-accent">
                  ({strings.uploadFlow.uploading} {uploadPercent}%)
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 self-start sm:self-center">
          {isDone && detectedLabel && (
            <Badge variant="ok">
              ✓ {strings.uploadFlow.detectedLabel}: {detectedLabel}
            </Badge>
          )}

          {doc.label_warning && (
            <Badge variant="warn">
              ⚠️ {doc.label_warning}
            </Badge>
          )}

          {isFailed && (
            <Badge variant="bad">
              ! {strings.uploadFlow.pipelineFailed}
            </Badge>
          )}

          {isProcessing && !isUploading && (
            <div className="flex items-center gap-1.5 text-xs text-accent">
              <Spinner size="sm" />
              <span>{doc.step_label_bn || strings.status.processing}</span>
            </div>
          )}
        </div>
      </div>

      {/* Upload Progress Bar (during initial client upload) */}
      {isUploading && (
        <div className="w-full bg-bg rounded-full h-2 overflow-hidden border border-line">
          <div
            className="bg-accent h-2 transition-all duration-200"
            style={{ width: `${uploadPercent}%` }}
          />
        </div>
      )}

      {/* Pipeline Strip (अपলোড → পড়া হচ্ছে → চেনা হচ্ছে → তথ্য বের হচ্ছে → শেষ) */}
      <div className="pt-1">
        <div className="grid grid-cols-5 gap-1 md:gap-2">
          {PIPELINE_STEPS.map((step, idx) => {
            const isCompleted = isDone || idx < currentStepIdx;
            const isCurrent = !isDone && !isFailed && idx === currentStepIdx;
            const isStepFailed = isFailed && idx === currentStepIdx;

            return (
              <div key={step.id} className="flex flex-col items-center text-center">
                <div
                  className={`w-full h-1.5 rounded-full mb-1.5 transition-colors ${
                    isCompleted
                      ? "bg-accent"
                      : isStepFailed
                      ? "bg-bad"
                      : isCurrent
                      ? "bg-accent animate-pulse"
                      : "bg-line/70"
                  }`}
                />
                <span
                  className={`text-[10px] md:text-xs leading-tight font-medium ${
                    isCompleted
                      ? "text-accent font-semibold"
                      : isStepFailed
                      ? "text-bad font-semibold"
                      : isCurrent
                      ? "text-ink font-bold"
                      : "text-muted"
                  }`}
                >
                  {step.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Stale Warning & Retry */}
      {doc.is_stale && !isFailed && (
        <div className="rounded-lg bg-warn-bg text-warn border border-warn/30 p-3 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <span>⚠️ {strings.uploadFlow.staleNotice}</span>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleReprocess}
            disabled={isReprocessing}
            className="bg-surface text-ink text-xs self-start sm:self-center"
          >
            {isReprocessing ? <Spinner size="sm" /> : strings.uploadFlow.retry}
          </Button>
        </div>
      )}

      {/* Failed Error Message & Action Buttons */}
      {isFailed && (
        <div className="rounded-xl bg-bad-bg border border-bad/30 p-3.5 space-y-3">
          <div className="text-xs md:text-sm text-bad leading-relaxed">
            <span className="font-bold">! </span>
            {doc.error_message || strings.status.failed}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              variant="primary"
              size="sm"
              onClick={handleReprocess}
              disabled={isReprocessing}
              className="text-xs bg-bad hover:bg-bad/90"
            >
              {isReprocessing ? <Spinner size="sm" /> : strings.uploadFlow.retry}
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => onRemove(doc.id)}
              className="text-xs bg-surface text-ink"
            >
              {strings.uploadFlow.remove}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
