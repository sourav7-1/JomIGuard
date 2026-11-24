"use client";

import { useState } from "react";
import { RISK_BN, recalledSample } from "@/lib/samples";
import { useLang } from "@/lib/lang";

const RISK_EN: Record<string, string> = { low: "Low risk", medium: "Medium risk", high: "High risk" };

// After a sample set was added on the upload page: expected (engine on the ground truth)
// vs. actual (what the app read and found). Hidden when no sample set was recorded here.
export function SampleCompare({ landId, risk, ruleIds }: { landId: string; risk: string; ruleIds: string[] }) {
  const en = useLang() === "en";
  const t = (b: string, e: string) => (en ? e : b);
  const [rec] = useState(() => recalledSample(landId));
  if (!rec) return null;
  const want = rec.expected.findings.map((f) => f.rule_id).sort().join(",");
  const riskOk = rec.expected.risk_level === risk;
  const allOk = riskOk && want === [...new Set(ruleIds)].sort().join(",");
  return (
    <p role="status" className={`rounded-[var(--radius-control)] border p-3 text-sm leading-6 ${allOk ? "border-ok/40 bg-ok-bg text-ink" : "border-warn/40 bg-warn-bg text-ink"}`}>
      <b>{t("নমুনা", "Sample")} “{rec.title}”:</b> {t("প্রত্যাশিত", "expected")}: {(en ? RISK_EN : RISK_BN)[rec.expected.risk_level] ?? rec.expected.risk_level} · {t("পাওয়া গেছে", "found")}: {(en ? RISK_EN : RISK_BN)[risk] ?? risk} {riskOk ? "✓" : "✗"}
      {!allOk && riskOk && <span className="block text-muted">{t("ঝুঁকির মাত্রা মিলেছে, তবে ফলাফলের তালিকা পুরো এক নয়।", "The risk level matched, but the list of findings is not identical.")}</span>}
      {!riskOk && <span className="block text-muted">{t("মেলেনি: কোনো কাগজ হয়তো ঠিকমতো পড়া যায়নি। নিচের ফলাফল ও “উৎস” দেখুন।", "Did not match: a paper may not have been read correctly. See the findings and “Source” below.")}</span>}
    </p>
  );
}
