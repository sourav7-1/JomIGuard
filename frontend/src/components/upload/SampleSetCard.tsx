"use client";

import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { useToast } from "@/components/ui/Toast";
import type { DropZoneHandle } from "@/components/upload/DocumentDropZone";
import { bnDigits } from "@/lib/digits";
import { RISK_BN, fetchSampleFile, rememberSample, sampleScenarios, type SampleSetInfo } from "@/lib/samples";
import { useLang } from "@/lib/lang";

// Option A (full set) and C (ZIP). The files are rendered on the server for THIS case's
// mouza / dag / khatian / upazila and uploaded through the drop zone's own upload path.
export function SampleSetCard({ landId, dropZone, hasDocuments }: {
  landId: string;
  dropZone: React.RefObject<DropZoneHandle | null>;
  hasDocuments: boolean;
}) {
  const en = useLang() === "en";
  const t = (b: string, e: string) => (en ? e : b);
  const toast = useToast();
  const [scenario, setScenario] = useState<string>("A");
  const [busy, setBusy] = useState<string | null>(null);

  const addSet = async () => {
    const pick = sampleScenarios.find((s) => s.id === scenario)!;
    try {
      setBusy(t("নমুনা সেট তৈরি হচ্ছে…", "Building sample set…"));
      const res = await fetch(`/api/demo/lands/${landId}/sample-sets/${scenario}`, { credentials: "include" });
      const info = (await res.json()) as SampleSetInfo & { detail?: string };
      if (!res.ok) throw new Error(info.detail ?? t("নমুনা সেট আনা যায়নি।", "Could not fetch the sample set."));
      for (const [i, f] of info.files.entries()) {
        setBusy(en ? `Adding papers: ${i + 1} / ${info.files.length}` : `কাগজ যোগ হচ্ছে: ${bnDigits(i + 1)} / ${bnDigits(info.files.length)}`);
        const file = await fetchSampleFile(`/api/demo/lands/${landId}/sample-sets/${scenario}/${f.name}`, f.name);
        await dropZone.current?.addFiles([file], f.doc_type);
      }
      rememberSample(landId, { scenario, title: pick.title, expected: info.expected });
      toast("ok", en ? `Sample set “${pick.en}” added. Press “Run check” once reading is done.` : `“${pick.title}” নমুনা সেট যোগ হয়েছে। পড়া শেষ হলে “যাচাই করুন” চাপুন।`);
    } catch (e) {
      toast("bad", e instanceof Error ? e.message : t("নমুনা সেট যোগ করা যায়নি।", "Could not add the sample set."));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div id="samples" className="scroll-mt-28">
      <Card
        title={t("নমুনা কাগজ দিয়ে চেষ্টা করুন", "Try with sample documents")}
        titleAs="h2"
        description={t("সব কাগজ কাল্পনিক, শুধু পরীক্ষার জন্য। কাগজগুলো এই কেসের মৌজা, দাগ ও খতিয়ান দিয়েই তৈরি হয়।", "All documents are synthetic, for testing only, made with this case's mouza, dag and khatian.")}
        footer={
          <div className="flex flex-wrap items-center gap-2">
            <button type="button" onClick={() => void addSet()} disabled={!!busy}
              className="inline-flex min-h-11 flex-col justify-center rounded-[var(--radius-control)] bg-accent px-4 py-1 text-sm font-semibold text-white shadow-rest hover:shadow-raised disabled:opacity-60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
              {busy ?? t("এই নমুনা সেট যোগ করুন", "Add this sample set")}
            </button>
            <a href={`/api/demo/lands/${landId}/samples.zip`} download
              className="inline-flex min-h-11 flex-col justify-center rounded-[var(--radius-control)] border border-line bg-surface px-3 py-1 text-sm font-semibold text-ink hover:bg-bg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
              {t("নমুনা ফাইল ডাউনলোড (ZIP)", "Download sample files (ZIP)")}
            </a>
          </div>
        }
      >
        <fieldset className="space-y-2">
          <legend className="sr-only">{t("নমুনা পরিস্থিতি বেছে নিন", "Choose a scenario")}</legend>
          {sampleScenarios.map((s) => (
            <label key={s.id}
              className={`flex cursor-pointer items-start gap-3 rounded-[var(--radius-control)] border p-3 text-sm transition-colors has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-accent ${scenario === s.id ? "border-accent bg-accent-soft/50" : "border-line bg-bg/40 hover:bg-bg"}`}>
              <input type="radio" name="sample-scenario" value={s.id} checked={scenario === s.id} onChange={() => setScenario(s.id)} className="mt-1 accent-[var(--color-accent)]" />
              <span className="min-w-0">
                <b className="text-ink">{en ? s.en : s.title}</b>
                <span className="block text-muted">{t("যা দেখবেন", "What you will see")}: {en ? s.seeEn : s.see}</span>
              </span>
            </label>
          ))}
        </fieldset>
        {hasDocuments && (
          <p className="mt-3 rounded-[var(--radius-control)] bg-warn-bg p-3 text-xs leading-5 text-warn">
            {t("এই কেসে আগে থেকেই কাগজ আছে; প্রত্যাশিত ফল শুধু এই নমুনা সেটের কাগজ থাকলে মিলবে। পরিষ্কার তুলনার জন্য নতুন কেস নিন।", "This case already has documents; the expected result assumes only this set. Use a new case for a clean comparison.")}
          </p>
        )}
        <p className="mt-3 text-xs text-muted">{en ? "High, medium or low risk: after the check, the result page compares it with the expected result." : `${RISK_BN.high}, ${RISK_BN.medium} বা ${RISK_BN.low}: যাচাইয়ের পর ফলাফলের পাতায় প্রত্যাশিত ফলের সঙ্গে মিলিয়ে দেখানো হবে।`}</p>
      </Card>
    </div>
  );
}
