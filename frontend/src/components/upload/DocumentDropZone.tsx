"use client";

import React, { useImperativeHandle, useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import {
  prepareFileForUpload,
  uploadDocumentWithProgress,
  validateFilePrecheck,
} from "@/lib/upload";
import type { DocumentStatusOut } from "@/lib/api";
import { fetchSampleFile } from "@/lib/samples";
import { En } from "@/components/ui/En";
import { useLang, useStrings } from "@/lib/lang";

export interface PendingUpload {
  id: string;
  name: string;
  progress: number;
  status: "optimizing" | "uploading" | "done" | "error";
  error?: string;
  docType?: string;
}

/** Lets the sample card add files through this same upload path (same checks, API and progress). */
export interface DropZoneHandle {
  addFiles: (files: File[], docType: string) => Promise<void>;
}

// "prior_deed" is only a UI choice: it uploads as doc_type "deed".
const uploadType = (t: string) => (t === "unknown" ? undefined : t === "prior_deed" ? "deed" : t);

export interface DocumentDropZoneProps {
  ref?: React.Ref<DropZoneHandle>;
  landId: string;
  onUploadSuccess: (doc: DocumentStatusOut, uploadId: string) => void;
  onUploadStart?: (upload: PendingUpload) => void;
  onUploadProgress?: (id: string, progress: number) => void;
  onUploadError?: (id: string, error: string) => void;
  className?: string;
}

export function DocumentDropZone({
  landId,
  onUploadSuccess,
  onUploadStart,
  onUploadProgress,
  onUploadError,
  className = "",
  ref,
}: DocumentDropZoneProps) {
  const strings = useStrings();
  const en = useLang() === "en";
  const t = (b: string, e: string) => (en ? e : b);
  const [selectedDocType, setSelectedDocType] = useState<string>("unknown");
  const [isDragging, setIsDragging] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [isProcessingFiles, setIsProcessingFiles] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  const handleFiles = async (files: FileList | File[], docType: string = selectedDocType) => {
    setLocalError(null);
    if (!files || files.length === 0) return;

    setIsProcessingFiles(true);
    const fileList = Array.from(files);

    for (const file of fileList) {
      // 1. Client-side precheck (type and max size for non-image)
      const check = validateFilePrecheck(file);
      if (!check.valid) {
        setLocalError(check.error || strings.uploadFlow.errGenericUpload);
        continue;
      }

      const tempId = `temp-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
      const pendingItem: PendingUpload = {
        id: tempId,
        name: file.name,
        progress: 0,
        status: "optimizing",
        docType: uploadType(docType),
      };

      onUploadStart?.(pendingItem);

      try {
        // 2. Downscale image in browser if > 10MB or > 3000px
        const fileToUpload = await prepareFileForUpload(file);

        // 3. Update status to uploading
        onUploadProgress?.(tempId, 5);

        // 4. Upload with XHR tracking upload percentage
        const uploadedDoc = await uploadDocumentWithProgress(fileToUpload, {
          landId,
          docType: uploadType(docType),
          onProgress: (percent) => {
            onUploadProgress?.(tempId, percent);
          },
        });

        onUploadSuccess(uploadedDoc, tempId);
      } catch (err: unknown) {
        const errorMsg =
          err instanceof Error ? err.message : strings.uploadFlow.errGenericUpload;
        onUploadError?.(tempId, errorMsg);
        setLocalError(errorMsg);
      }
    }

    setIsProcessingFiles(false);
    // Reset file inputs
    if (fileInputRef.current) fileInputRef.current.value = "";
    if (cameraInputRef.current) cameraInputRef.current.value = "";
  };

  useImperativeHandle(ref, () => ({ addFiles: (files, docType) => handleFiles(files, docType) }));

  // Option B: one synthetic sample of the selected type, rendered for this land.
  const [loadingSample, setLoadingSample] = useState(false);
  const addSample = async () => {
    if (selectedDocType === "unknown") {
      setLocalError(t("নমুনা নিতে আগে বেছে নিন কোন কাগজ।", "Pick a document type first."));
      return;
    }
    setLoadingSample(true);
    setLocalError(null);
    try {
      const file = await fetchSampleFile(`/api/demo/lands/${landId}/samples/${selectedDocType}.png`, `sample-${selectedDocType}.png`);
      await handleFiles([file], selectedDocType);
    } catch (e) {
      setLocalError(e instanceof Error ? e.message : strings.uploadFlow.errGenericUpload);
    } finally {
      setLoadingSample(false);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files) {
      handleFiles(e.dataTransfer.files);
    }
  };

  return (
    <div className={`space-y-3 ${className}`}>
      {/* File type selector before upload */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-surface p-3 rounded-xl border border-line">
        <label
          htmlFor="doc-type-select"
          className="text-xs md:text-sm font-medium text-ink flex items-center gap-1.5"
        >
          <span>📋</span> {strings.uploadFlow.docTypeQuestion}
        </label>
        <div className="flex flex-wrap items-center gap-2">
        <select
          id="doc-type-select"
          value={selectedDocType}
          onChange={(e) => setSelectedDocType(e.target.value)}
          className="min-h-[44px] px-3 py-2 text-sm rounded-lg border border-line bg-bg text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent cursor-pointer"
        >
          <option value="unknown">{strings.uploadFlow.docTypeUnknown}</option>
          <option value="khatian">{strings.uploadFlow.docTypeKhatian}</option>
          <option value="deed">{strings.uploadFlow.recDraftDeed}</option>
          <option value="prior_deed">{strings.uploadFlow.recPriorDeed}{en ? "" : " (আগের দলিল)"}</option>
          <option value="dcr">{strings.uploadFlow.docTypeDcr}</option>
          <option value="heir_cert">{strings.uploadFlow.docTypeHeirCert}</option>
        </select>
        <button
          type="button"
          onClick={() => void addSample()}
          disabled={loadingSample || isProcessingFiles}
          className="min-h-[44px] rounded-lg px-2 text-left text-xs font-semibold text-accent underline underline-offset-4 hover:no-underline disabled:opacity-60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          {loadingSample ? t("নমুনা আনা হচ্ছে…", "Fetching sample…") : t("নমুনা ফাইল নিন", "Get a sample file")}
          <En className="no-underline">Use a sample</En>
        </button>
        </div>
      </div>

      {/* Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`relative border-2 border-dashed rounded-2xl p-6 md:p-8 text-center transition-all ${
          isDragging
            ? "border-accent bg-accent-soft/40 scale-[1.01]"
            : "border-line bg-surface/70 hover:border-accent/40 hover:bg-surface"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          id="file-upload-input"
          accept="image/jpeg,image/png,image/webp,application/pdf"
          multiple
          className="sr-only"
          onChange={(e) => e.target.files && handleFiles(e.target.files)}
        />
        {/* Mobile camera input with capture="environment" */}
        <input
          ref={cameraInputRef}
          type="file"
          id="camera-upload-input"
          accept="image/*"
          capture="environment"
          className="sr-only"
          onChange={(e) => e.target.files && handleFiles(e.target.files)}
        />

        <div className="flex flex-col items-center justify-center space-y-3">
          <div className="w-14 h-14 rounded-full bg-accent-soft text-accent flex items-center justify-center text-2xl" aria-hidden="true">
            📂
          </div>

          <div className="space-y-1">
            <p className="text-sm md:text-base font-semibold text-ink">
              {strings.uploadFlow.dropZonePrompt}
            </p>
            <p className="text-xs text-muted max-w-sm mx-auto leading-relaxed">
              {strings.uploadFlow.supportedFormats}
            </p>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            <Button
              type="button"
              variant="primary"
              disabled={isProcessingFiles}
              onClick={() => fileInputRef.current?.click()}
              className="gap-2"
            >
              <span>📁</span> {strings.uploadFlow.browseFiles}
            </Button>

            {/* Separate Phone Camera Button */}
            <Button
              type="button"
              variant="ghost"
              disabled={isProcessingFiles}
              onClick={() => cameraInputRef.current?.click()}
              className="gap-2 bg-surface"
            >
              <span>📷</span> {strings.uploadFlow.takePhoto}
            </Button>
          </div>
        </div>
      </div>

      {/* Error display if any */}
      {localError && (
        <div
          role="alert"
          className="text-xs md:text-sm text-bad bg-bad-bg border border-bad/30 rounded-lg p-3 flex items-start gap-2"
        >
          <span className="font-bold">!</span>
          <span>{localError}</span>
        </div>
      )}

      {/* Honest Privacy Notice */}
      <p className="text-xs text-muted text-center leading-relaxed px-2">
        {strings.uploadFlow.privacyHonest}
      </p>
    </div>
  );
}
