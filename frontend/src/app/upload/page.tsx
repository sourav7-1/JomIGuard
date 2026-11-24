"use client";

import React, { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { api } from "@/lib/api";
import { divisions } from "@/lib/bd-locations";
import { useLang, useStrings } from "@/lib/lang";

export default function NewCheckPage() {
  return <Suspense><NewCheckForm /></Suspense>;
}

function NewCheckForm() {
  const strings = useStrings();
  const en = useLang() === "en";
  const t = (b: string, e: string) => (en ? e : b);
  const router = useRouter();
  // pre-filled from the location picker (/find)
  const params = useSearchParams();
  const [district, setDistrict] = useState(params.get("district")?.trim() ?? "");
  const khatianNo = params.get("khatian")?.trim() ?? "";

  const [mouza, setMouza] = useState(params.get("mouza") ?? "");
  const [dagNo, setDagNo] = useState(params.get("dag") ?? "");
  const [upazila, setUpazila] = useState(params.get("upazila") ?? "");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const trimmedMouza = mouza.trim();
    if (!district) {
      setError(t("জেলা বেছে নিন।", "Choose a district."));
      return;
    }
    if (!trimmedMouza) {
      setError(strings.uploadFlow.mouzaRequired);
      return;
    }

    setIsSubmitting(true);
    try {
      const land = await api.createLand({
        mouza: trimmedMouza,
        dag_no: dagNo.trim(),
        upazila: upazila.trim(),
        district,
        ...(khatianNo && { khatian_no: khatianNo }),
      });

      router.push(`/upload/${land.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : strings.error.defaultMessage);
      setIsSubmitting(false);
    }
  };

  return (
    <div className="mx-auto grid max-w-5xl gap-7 py-2 md:grid-cols-[0.8fr_1.2fr] md:items-start md:gap-14">
      {/* Step Header */}
      <div className="space-y-3 md:pt-5">
        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-accent-soft text-accent text-xs font-semibold mb-1">
          <span>{t("ধাপ ১", "Step 1")}</span> • {strings.uploadFlow.step1Title}
        </div>
        <h1 className="text-2xl md:text-3xl font-bold font-heading text-ink">
          {strings.uploadFlow.step1Title}
        </h1>
        <p className="text-sm text-muted leading-relaxed">
          {strings.uploadFlow.step1Subtitle}
        </p>
      </div>

      <Card className="p-5 md:p-8">
        <form onSubmit={handleSubmit} className="space-y-5">
          {khatianNo && (
            <p className="rounded-lg bg-accent-soft px-3 py-2 text-sm text-ink">{t("খতিয়ান নং", "Khatian no.")}: <b>{khatianNo}</b></p>
          )}
          <div className="space-y-1.5">
            <label htmlFor="district-input" className="block text-sm font-semibold text-ink">
              {t("জেলা", "District")} <span className="text-bad">*</span>
            </label>
            <select
              id="district-input"
              required
              value={district}
              onChange={(e) => setDistrict(e.target.value)}
              className="w-full min-h-[44px] px-3.5 py-2.5 rounded-lg border border-line bg-bg text-ink text-sm"
            >
              <option value="">{t("জেলা বেছে নিন", "Choose a district")}</option>
              {divisions.map((d) => (
                <optgroup key={d.name} label={`${d.name} ${t("বিভাগ", "Division")}`}>
                  {d.districts.map((name) => <option key={name}>{name}</option>)}
                </optgroup>
              ))}
            </select>
          </div>
          {/* Mouza (Required) */}
          <div className="space-y-1.5">
            <label
              htmlFor="mouza-input"
              className="block text-sm font-semibold text-ink"
            >
              {strings.uploadFlow.mouzaLabel} <span className="text-bad">*</span>
            </label>
            <input
              id="mouza-input"
              type="text"
              required
              value={mouza}
              onChange={(e) => setMouza(e.target.value)}
              placeholder={strings.uploadFlow.mouzaPlaceholder}
              className="w-full min-h-[44px] px-3.5 py-2.5 rounded-lg border border-line bg-bg text-ink placeholder:text-muted/60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent text-sm"
            />
          </div>

          {/* Dag No (Optional, Bangla or English digits) */}
          <div className="space-y-1.5">
            <label
              htmlFor="dag-input"
              className="block text-sm font-semibold text-ink"
            >
              {strings.uploadFlow.dagLabel}
            </label>
            <input
              id="dag-input"
              type="text"
              value={dagNo}
              onChange={(e) => setDagNo(e.target.value)}
              placeholder={strings.uploadFlow.dagPlaceholder}
              className="w-full min-h-[44px] px-3.5 py-2.5 rounded-lg border border-line bg-bg text-ink placeholder:text-muted/60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent text-sm"
            />
            <p className="text-[11px] text-muted">
              {t("বাংলা বা ইংরেজি সংখ্যায় লিখতে পারেন", "Bangla or English digits both work")}
            </p>
          </div>

          {/* Upazila (Optional) */}
          <div className="space-y-1.5">
            <label
              htmlFor="upazila-input"
              className="block text-sm font-semibold text-ink"
            >
              {strings.uploadFlow.upazilaLabel}
            </label>
            <input
              id="upazila-input"
              type="text"
              value={upazila}
              onChange={(e) => setUpazila(e.target.value)}
              placeholder={strings.uploadFlow.upazilaPlaceholder}
              className="w-full min-h-[44px] px-3.5 py-2.5 rounded-lg border border-line bg-bg text-ink placeholder:text-muted/60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent text-sm"
            />
          </div>

          {error && (
            <div
              role="alert"
              className="text-xs text-bad bg-bad-bg border border-bad/30 rounded-lg p-3 flex items-center gap-2"
            >
              <span className="font-bold">!</span>
              <span>{error}</span>
            </div>
          )}

          <Button
            type="submit"
            variant="primary"
            disabled={isSubmitting}
            className="w-full min-h-[48px] text-base font-semibold"
          >
            {isSubmitting ? (
              <span className="flex items-center gap-2">
                <Spinner size="sm" />
                {strings.uploadFlow.submittingStep1}
              </span>
            ) : (
              strings.uploadFlow.submitStep1
            )}
          </Button>
        </form>
      </Card>
    </div>
  );
}
