"use client";

import React from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import type { DocumentStatusOut } from "@/lib/api";
import { strings } from "@/lib/strings";

export interface RecommendedDocListProps {
  documents: DocumentStatusOut[];
  onAssess: () => void;
  isAssessing?: boolean;
  assessError?: string | null;
  className?: string;
}

export function RecommendedDocList({
  documents,
  onAssess,
  isAssessing = false,
  assessError,
  className = "",
}: RecommendedDocListProps) {
  // Check which types are satisfied by finished documents
  const doneDocs = documents.filter((d) => d.status === "done");

  const hasCurrentKhatian = doneDocs.some(
    (d) => d.detected_doc_type === "khatian" || d.doc_type === "khatian"
  );

  const deedDocs = doneDocs.filter(
    (d) => d.detected_doc_type === "deed" || d.doc_type === "deed"
  );
  const hasDraftDeed = deedDocs.length > 0;
  const hasPriorDeed = deedDocs.length > 1;

  const hasMutation = doneDocs.some(
    (d) => d.detected_doc_type === "dcr" || d.doc_type === "dcr"
  );

  const hasHeirCert = doneDocs.some(
    (d) => d.detected_doc_type === "heir_cert" || d.doc_type === "heir_cert"
  );

  const recommendedItems = [
    { id: "khatian", label: strings.uploadFlow.recCurrentKhatian, checked: hasCurrentKhatian },
    { id: "draft_deed", label: strings.uploadFlow.recDraftDeed, checked: hasDraftDeed },
    { id: "prior_deed", label: strings.uploadFlow.recPriorDeed, checked: hasPriorDeed },
    { id: "mutation", label: strings.uploadFlow.recMutation, checked: hasMutation },
    { id: "heir_cert", label: strings.uploadFlow.recHeirCert, checked: hasHeirCert },
  ];

  const hasDocuments = documents.length > 0;
  const hasProcessing = documents.some(
    (d) => d.status === "processing" || d.status === "uploaded"
  );
  const canAssess = hasDocuments && !hasProcessing && doneDocs.length > 0 && !isAssessing;

  return (
    <Card className={`space-y-4 p-5 ${className}`}>
      <div className="space-y-1 border-b border-line pb-3">
        <h3 className="text-sm md:text-base font-bold font-heading text-ink flex items-center gap-1.5">
          <span>📋</span> {strings.uploadFlow.recommendedTitle}
        </h3>
        <p className="text-xs text-muted leading-relaxed">
          কাগজের ধরন চিহ্নিত হলে পাশের বক্সে টিকচিহ্ন আসবে
        </p>
      </div>

      <ul className="space-y-2.5">
        {recommendedItems.map((item) => (
          <li key={item.id} className="flex items-center gap-2.5 text-xs md:text-sm">
            <span
              className={`w-5 h-5 rounded-md flex items-center justify-center font-bold text-xs transition-colors ${
                item.checked
                  ? "bg-ok text-white"
                  : "bg-surface border border-line text-transparent"
              }`}
              aria-hidden="true"
            >
              ✓
            </span>
            <span className={item.checked ? "text-ink font-semibold" : "text-muted"}>
              {item.label}
            </span>
          </li>
        ))}
      </ul>

      {/* Assess Action Section */}
      <div className="pt-3 border-t border-line space-y-2">
        <Button
          type="button"
          variant="primary"
          disabled={!canAssess}
          onClick={onAssess}
          className="w-full text-sm font-semibold py-3"
        >
          {isAssessing ? (
            <span className="flex items-center gap-2">
              <Spinner size="sm" />
              {strings.uploadFlow.assessingButton}
            </span>
          ) : (
            strings.uploadFlow.assessButton
          )}
        </Button>

        {!hasDocuments && (
          <p className="text-[11px] text-muted text-center leading-tight">
            {strings.uploadFlow.needAtLeastOneDoc}
          </p>
        )}

        {hasDocuments && hasProcessing && (
          <p className="text-[11px] text-accent text-center leading-tight flex items-center justify-center gap-1.5">
            <Spinner size="sm" />
            <span>{strings.uploadFlow.waitingForDocs}</span>
          </p>
        )}

        {assessError && (
          <p className="text-[11px] text-bad text-center leading-tight">
            {assessError}
          </p>
        )}
      </div>
    </Card>
  );
}
