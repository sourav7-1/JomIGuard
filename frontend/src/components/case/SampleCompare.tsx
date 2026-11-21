"use client";

import { useState } from "react";
import { En } from "@/components/ui/En";
import { RISK_BN, recalledSample } from "@/lib/samples";

// After a sample set was added on the upload page: expected (engine on the ground truth)
// vs. actual (what the app read and found). Hidden when no sample set was recorded here.
export function SampleCompare({ landId, risk, ruleIds }: { landId: string; risk: string; ruleIds: string[] }) {
  const [rec] = useState(() => recalledSample(landId));
  if (!rec) return null;
  const want = rec.expected.findings.map((f) => f.rule_id).sort().join(",");
  const riskOk = rec.expected.risk_level === risk;
  const allOk = riskOk && want === [...new Set(ruleIds)].sort().join(",");
  return (
    <p role="status" className={`rounded-[var(--radius-control)] border p-3 text-sm leading-6 ${allOk ? "border-ok/40 bg-ok-bg text-ink" : "border-warn/40 bg-warn-bg text-ink"}`}>
      <b>নমুনা “{rec.title}”:</b> প্রত্যাশিত: {RISK_BN[rec.expected.risk_level] ?? rec.expected.risk_level} · পাওয়া গেছে: {RISK_BN[risk] ?? risk} {riskOk ? "✓" : "✗"}
      {!allOk && riskOk && <span className="block text-muted">ঝুঁকির মাত্রা মিলেছে, তবে ফলাফলের তালিকা পুরো এক নয়।</span>}
      {!riskOk && <span className="block text-muted">মেলেনি: কোনো কাগজ হয়তো ঠিকমতো পড়া যায়নি। নিচের ফলাফল ও “উৎস” দেখুন।</span>}
      <En className="text-muted">Sample set: expected vs. actual{allOk ? " (all findings match)" : ""}.</En>
    </p>
  );
}
