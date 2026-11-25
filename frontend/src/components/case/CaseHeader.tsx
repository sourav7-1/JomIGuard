"use client";

import React from "react";
import { LandCaseViewOut } from "@/lib/api";
import { bnDigits } from "@/lib/digits";
import { useLang, useStrings } from "@/lib/lang";

interface CaseHeaderProps {
  caseView: LandCaseViewOut;
}

/** Title, location and the page purpose. Stale data is shown by the journey (step 3). */
export function CaseHeader({ caseView }: CaseHeaderProps) {
  const strings = useStrings();
  const en = useLang() === "en";
  const t = (b: string, e: string) => (en ? e : b);

  const land = caseView.land;

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
                {t("দাগ", "Dag")} {en ? land.dag_no : bnDigits(land.dag_no)}
              </span>
            )}
            {land.khatian_no && (
              <span className="text-sm md:text-base font-mono bg-bg/80 px-2 py-0.5 rounded border border-line">
                {t("খতিয়ান", "Khatian")} {en ? land.khatian_no : bnDigits(land.khatian_no)}
              </span>
            )}
          </h1>
          <p className="text-xs md:text-sm text-muted">
            {t("উপজেলা", "Upazila")}: {land.upazila || "—"}, {t("জেলা", "District")}: {land.district || "—"}
          </p>
          <p className="text-sm text-ink">{t("এই জমির যাচাই ধাপে ধাপে; যে ধাপে আপনার কাজ বাকি, সেটি খোলা আছে।", "This plot's check, step by step; the step that needs you is open.")}</p>
        </div>

      </div>

    </div>
  );
}
