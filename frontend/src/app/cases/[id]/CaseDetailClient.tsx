"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  api,
  CaseViewDocOut,
  CaseViewExtractionOut,
  FieldsMetaResponse,
  LandCaseViewOut,
} from "@/lib/api";
import { strings } from "@/lib/strings";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState } from "@/components/ui/EmptyState";
import { VerdictBox } from "@/components/ui/VerdictBox";
import { CheckItem } from "@/components/ui/CheckItem";
import { Card } from "@/components/ui/Card";
import {
  CaseHeader,
  CaseSummaryTable,
  DocumentFieldsPanel,
} from "@/components/case";

interface CaseDetailClientProps {
  landId: string;
}

export function CaseDetailClient({ landId }: CaseDetailClientProps) {
  const [caseView, setCaseView] = useState<LandCaseViewOut | null>(null);
  const [fieldsMeta, setFieldsMeta] = useState<FieldsMetaResponse | null>(null);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [cv, meta] = await Promise.all([
        api.getLandCaseView(landId),
        api.getFieldsMeta(),
      ]);
      setCaseView(cv);
      setFieldsMeta(meta);

      if (cv.documents.length > 0) {
        setSelectedDocId((prev) => {
          if (prev && cv.documents.some((d) => d.id === prev)) {
            return prev;
          }
          return cv.documents[0].id;
        });
      }
    } catch {
      setError("কেসের তথ্য লোড করতে সমস্যা হয়েছে।");
    } finally {
      setLoading(false);
    }
  }, [landId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleExtractionUpdated = useCallback(
    (_docId: string, _newExtraction: CaseViewExtractionOut) => {
      // Re-fetch to update staleness and document data cleanly
      fetchData();
    },
    [fetchData]
  );

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-3">
        <Spinner size="lg" />
        <span className="text-sm text-muted">{strings.labels.loading}</span>
      </div>
    );
  }

  if (error || !caseView) {
    return (
      <div className="max-w-2xl mx-auto py-12">
        <EmptyState
          title="কেসটি পাওয়া যায়নি"
          description={error || "অনুগ্রহ করে সঠিক কেস আইডি দিয়ে পুনরায় চেষ্টা করুন।"}
          actionLabel="নতুন যাচাই শুরু করুন"
          actionHref="/upload"
        />
      </div>
    );
  }

  if (caseView.documents.length === 0) {
    return (
      <div className="max-w-3xl mx-auto py-6 space-y-6">
        <CaseHeader caseView={caseView} onAssessmentTriggered={fetchData} />
        <EmptyState
          title={strings.casePage.emptyDocList}
          description="যাচাই সম্পন্ন করতে প্রয়োজনীয় দলিল ও খতিয়ান আপলোড করুন।"
          actionLabel={strings.casePage.addDocLink}
          actionHref={`/upload/${landId}`}
        />
      </div>
    );
  }

  const selectedDoc =
    caseView.documents.find((d) => d.id === selectedDocId) || caseView.documents[0];

  const docType = selectedDoc?.doc_type || "khatian";
  const fieldMetaList = fieldsMeta ? (fieldsMeta as Record<string, typeof fieldsMeta.khatian>)[docType] || [] : [];

  return (
    <div className="max-w-6xl mx-auto py-4 space-y-6">
      {/* 1. Header: title, stale banner & re-assess button */}
      <CaseHeader caseView={caseView} onAssessmentTriggered={fetchData} />

      {/* 2. Verdict & Findings Placeholder for Day 36 */}
      <div className="space-y-3 bg-surface p-4 rounded-xl border border-line">
        <div className="flex items-center justify-between">
          <h3 className="font-heading font-bold text-base text-ink">
            {strings.casePage.placeholderVerdictTitle}
          </h3>
          <span className="text-xs text-muted bg-bg px-2 py-0.5 rounded border border-line">
            ডে ৩৬-এ সক্রিয় হবে
          </span>
        </div>
        <p className="text-xs text-muted leading-relaxed">
          {strings.casePage.placeholderVerdictDesc}
        </p>

        {caseView.latest_assessment ? (
          <VerdictBox
            riskLevel={caseView.latest_assessment.risk_level as "low" | "medium" | "high"}
            title={caseView.latest_assessment.headline_bn}
            summary={caseView.latest_assessment.summary_bn}
          />
        ) : (
          <div className="space-y-2 pt-1">
            <CheckItem
              status="ok"
              title="কাগজপত্র আপলোড সম্পন্ন"
              description="সকল সংযুক্ত দলিলের প্রাথমিক রিডিং প্রস্তুত।"
            />
            <CheckItem
              status="warn"
              title="তথ্য মিলিয়ে দেখা বাকি"
              description="মূল কাগজের সাথে এক্সট্রাক্টকৃত তথ্য মিলিয়ে সংরক্ষণ করুন।"
            />
          </div>
        )}
      </div>

      {/* 3. Summary table: Land Case File */}
      <CaseSummaryTable
        documents={caseView.documents}
        selectedDocId={selectedDoc.id}
        onSelectDoc={setSelectedDocId}
      />

      {/* 4. Document selector tabs */}
      <div className="space-y-3">
        <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
          {caseView.documents.map((d: CaseViewDocOut) => {
            const isSelected = d.id === selectedDoc.id;
            return (
              <button
                key={d.id}
                type="button"
                onClick={() => setSelectedDocId(d.id)}
                className={`px-3.5 py-2 rounded-xl text-xs font-semibold whitespace-nowrap transition-colors flex items-center gap-1.5 min-h-[44px] border ${
                  isSelected
                    ? "bg-accent text-surface border-accent shadow-xs"
                    : "bg-surface text-ink border-line hover:bg-bg"
                }`}
              >
                <span>{d.label_bn}</span>
              </button>
            );
          })}
        </div>

        {/* 5. Document Panel: Image with Zoom/Pan next to Fields */}
        <DocumentFieldsPanel
          key={selectedDoc.id}
          document={selectedDoc}
          fieldMetaList={fieldMetaList}
          onExtractionUpdated={handleExtractionUpdated}
        />
      </div>

      {/* Link to Upload more docs */}
      <Card className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-bg/50">
        <div className="text-xs text-muted">
          আরো কোনো দলিল বা খতিয়ান যোগ করতে চান?
        </div>
        <Link
          href={`/upload/${landId}`}
          className="text-xs font-semibold text-accent hover:underline flex items-center gap-1 min-h-[44px] px-3 py-2 border border-line rounded-lg bg-surface self-start sm:self-auto"
        >
          + আরো কাগজ যোগ করুন
        </Link>
      </Card>
    </div>
  );
}
