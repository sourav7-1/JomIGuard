"use client";

import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { En } from "@/components/ui/En";
import { useToast } from "@/components/ui/Toast";
import type { DropZoneHandle } from "@/components/upload/DocumentDropZone";
import { bnDigits } from "@/lib/digits";
import { RISK_BN, fetchSampleFile, rememberSample, sampleScenarios, type SampleSetInfo } from "@/lib/samples";

// Option A (full set) and C (ZIP). The files are rendered on the server for THIS case's
// mouza / dag / khatian / upazila and uploaded through the drop zone's own upload path.
export function SampleSetCard({ landId, dropZone, hasDocuments }: {
  landId: string;
  dropZone: React.RefObject<DropZoneHandle | null>;
  hasDocuments: boolean;
}) {
  const toast = useToast();
  const [scenario, setScenario] = useState<string>("A");
  const [busy, setBusy] = useState<string | null>(null);

  const addSet = async () => {
    const pick = sampleScenarios.find((s) => s.id === scenario)!;
    try {
      setBusy("নমুনা সেট তৈরি হচ্ছে…");
      const res = await fetch(`/api/demo/lands/${landId}/sample-sets/${scenario}`, { credentials: "include" });
      const info = (await res.json()) as SampleSetInfo & { detail?: string };
      if (!res.ok) throw new Error(info.detail ?? "নমুনা সেট আনা যায়নি।");
      for (const [i, f] of info.files.entries()) {
        setBusy(`কাগজ যোগ হচ্ছে: ${bnDigits(i + 1)} / ${bnDigits(info.files.length)}`);
        const file = await fetchSampleFile(`/api/demo/lands/${landId}/sample-sets/${scenario}/${f.name}`, f.name);
        await dropZone.current?.addFiles([file], f.doc_type);
      }
      rememberSample(landId, { scenario, title: pick.title, expected: info.expected });
      toast("ok", `“${pick.title}” নমুনা সেট যোগ হয়েছে। পড়া শেষ হলে “যাচাই করুন” চাপুন।`);
    } catch (e) {
      toast("bad", e instanceof Error ? e.message : "নমুনা সেট যোগ করা যায়নি।");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div id="samples" className="scroll-mt-28">
      <Card
        title={<>নমুনা কাগজ দিয়ে চেষ্টা করুন<En className="text-muted">Try with sample documents</En></>}
        titleAs="h2"
        description={<>সব কাগজ কাল্পনিক, শুধু পরীক্ষার জন্য। কাগজগুলো এই কেসের মৌজা, দাগ ও খতিয়ান দিয়েই তৈরি হয়।<En>All documents are synthetic, made with this case&apos;s mouza, plot and khatian.</En></>}
        footer={
          <div className="flex flex-wrap items-center gap-2">
            <button type="button" onClick={() => void addSet()} disabled={!!busy}
              className="inline-flex min-h-11 flex-col justify-center rounded-[var(--radius-control)] bg-accent px-4 py-1 text-sm font-semibold text-white shadow-rest hover:shadow-raised disabled:opacity-60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
              {busy ?? "এই নমুনা সেট যোগ করুন"}<En>{busy ? "Adding…" : "Add this sample set"}</En>
            </button>
            <a href={`/api/demo/lands/${landId}/samples.zip`} download
              className="inline-flex min-h-11 flex-col justify-center rounded-[var(--radius-control)] border border-line bg-surface px-3 py-1 text-sm font-semibold text-ink hover:bg-bg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
              নমুনা ফাইল ডাউনলোড (ZIP)<En>Download samples, then drag them in yourself</En>
            </a>
          </div>
        }
      >
        <fieldset className="space-y-2">
          <legend className="sr-only">নমুনা পরিস্থিতি বেছে নিন (Choose a scenario)</legend>
          {sampleScenarios.map((s) => (
            <label key={s.id}
              className={`flex cursor-pointer items-start gap-3 rounded-[var(--radius-control)] border p-3 text-sm transition-colors has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-accent ${scenario === s.id ? "border-accent bg-accent-soft/50" : "border-line bg-bg/40 hover:bg-bg"}`}>
              <input type="radio" name="sample-scenario" value={s.id} checked={scenario === s.id} onChange={() => setScenario(s.id)} className="mt-1 accent-[var(--color-accent)]" />
              <span className="min-w-0">
                <b className="text-ink">{s.title}</b> <span lang="en" className="text-xs text-muted">· {s.en}</span>
                <span className="block text-muted">যা দেখবেন: {s.see}</span>
                <En className="text-muted">{s.seeEn}</En>
              </span>
            </label>
          ))}
        </fieldset>
        {hasDocuments && (
          <p className="mt-3 rounded-[var(--radius-control)] bg-warn-bg p-3 text-xs leading-5 text-warn">
            এই কেসে আগে থেকেই কাগজ আছে; প্রত্যাশিত ফল শুধু এই নমুনা সেটের কাগজ থাকলে মিলবে। পরিষ্কার তুলনার জন্য নতুন কেস নিন।
            <En>This case already has documents; the expected result assumes only this set. Use a new case for a clean comparison.</En>
          </p>
        )}
        <p className="mt-3 text-xs text-muted">{RISK_BN.high}, {RISK_BN.medium} বা {RISK_BN.low}: যাচাইয়ের পর ফলাফলের পাতায় প্রত্যাশিত ফলের সঙ্গে মিলিয়ে দেখানো হবে।<En>After the check, the result page compares expected and actual.</En></p>
      </Card>
    </div>
  );
}
