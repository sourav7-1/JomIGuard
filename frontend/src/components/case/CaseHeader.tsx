"use client";

import React, { useState } from "react";
import Link from "next/link";
import { api, LandCaseViewOut } from "@/lib/api";
import { strings } from "@/lib/strings";
import { Spinner } from "@/components/ui/Spinner";

interface CaseHeaderProps {
  caseView: LandCaseViewOut;
  onAssessmentTriggered: () => void;
}

export function CaseHeader({ caseView, onAssessmentTriggered }: CaseHeaderProps) {
  const [reassessing, setReassessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const land = caseView.land;

  const handleReAssess = async () => {
    setReassessing(true);
    setError(null);
    try {
      await api.assessLand(land.id);
      onAssessmentTriggered();
    } catch {
      setError(strings.uploadFlow.errAssess);
    } finally {
      setReassessing(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Top Title & Navigation */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="space-y-1">
          <h1 className="text-xl md:text-2xl font-bold font-heading text-ink flex items-center gap-2 flex-wrap">
            <span>{strings.casePage.titlePrefix}</span>
            <span className="text-accent">
              {land.mouza || strings.casePage.emptyValue}
            </span>
            {land.dag_no && (
              <span className="text-sm md:text-base font-mono bg-bg/80 px-2 py-0.5 rounded border border-line">
                দাগ {land.dag_no}
              </span>
            )}
            {land.khatian_no && (
              <span className="text-sm md:text-base font-mono bg-bg/80 px-2 py-0.5 rounded border border-line">
                খতিয়ান {land.khatian_no}
              </span>
            )}
          </h1>
          <p className="text-xs md:text-sm text-muted">
            উপজেলা: {land.upazila || "—"}, জেলা: {land.district || "—"}
          </p>
        </div>

        <Link
          href={`/cases/${land.id}/timeline`}
          className="min-h-[44px] px-4 py-2 rounded-lg border border-line bg-surface text-ink hover:bg-bg transition-colors flex items-center justify-center text-sm font-medium self-start sm:self-center focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          {strings.pages.caseDetail.timelineLink} →
        </Link>
      </div>

      {/* Stale Banner when information has changed */}
      {caseView.assessment_stale && (
        <div
          role="alert"
          className="p-4 rounded-xl border border-warn/40 bg-warn-bg flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs"
        >
          <div className="flex items-center gap-2 text-sm text-ink font-semibold">
            <span className="text-lg">⚠️</span>
            <span>{strings.casePage.staleBannerText}</span>
          </div>

          <button
            type="button"
            disabled={reassessing}
            onClick={handleReAssess}
            className="px-4 py-2 rounded-lg bg-accent text-surface text-xs font-bold hover:opacity-90 disabled:opacity-50 transition-opacity flex items-center justify-center gap-1.5 min-h-[44px] shrink-0"
          >
            {reassessing ? (
              <>
                <Spinner size="sm" />
                <span>{strings.casePage.reAssessingButton}</span>
              </>
            ) : (
              <span>{strings.casePage.reAssessButton}</span>
            )}
          </button>
        </div>
      )}

      {error && (
        <div className="p-3 text-xs rounded-lg bg-bad-bg/60 border border-bad/30 text-bad font-medium">
          {error}
        </div>
      )}
    </div>
  );
}
