"use client";

import React from "react";
import { LandCaseViewOut, SatelliteCheckOut } from "@/lib/api";
import { useLang, useStrings } from "@/lib/lang";
import { bnDigits } from "@/lib/digits";

type Item = { text: string; rank: number; actionId?: string; done?: boolean; who?: string; step?: number };

/** Everything the app already says to do next, most urgent first: blocking journey steps,
 *  then open rule actions (priority 1 first), then satellite next actions. */
export function nextItems(caseView: LandCaseViewOut, check: SatelliteCheckOut | null): Item[] {
  const out: Item[] = [];
  const docs = caseView.journey.steps[1];
  if (docs.status === "action" && docs.note_bn) out.push({ text: docs.note_bn, rank: 0, step: 2 });
  const paper = caseView.journey.steps[2];
  if (caseView.assessment_stale && paper.note_bn) out.push({ text: paper.note_bn, rank: 0, step: 3 });
  for (const a of caseView.latest_assessment?.actions ?? []) {
    // the OCR action leads to step 2, where "আবার চেষ্টা করুন" re-reads the documents
    out.push({ text: a.text_bn, rank: a.done ? 9 : a.priority, actionId: a.id, done: !!a.done, who: a.who,
      step: a.id === "verify_ocr_numbers" ? 2 : undefined });
  }
  for (const f of check?.status === "ok" ? check.findings ?? [] : []) {
    const text = f.values?.next_action_bn;
    if (typeof text === "string") out.push({ text, rank: f.status === "bad" ? 1 : f.status === "warn" ? 2 : 3, step: 4 });
  }
  const seen = new Set<string>();
  return out
    .map((a, i) => ({ ...a, i }))
    .sort((a, b) => a.rank - b.rank || a.i - b.i)
    .filter((a) => !seen.has(a.text) && seen.add(a.text));
}

export function NextActions({ caseView, check, busyId, onToggle, onGoToStep }: {
  caseView: LandCaseViewOut;
  check: SatelliteCheckOut | null;
  busyId: string | null;
  onToggle: (actionId: string, done: boolean) => void;
  onGoToStep: (n: number) => void;
}) {
  const en = useLang() === "en";
  const strings = useStrings();
  const items = nextItems(caseView, check);
  const open = items.filter((i) => !i.done);
  const top = open.slice(0, 3);
  const rest = items.filter((i) => !top.includes(i));

  const row = (item: Item) => (
    <li key={item.text} className="flex min-h-11 items-start gap-3 text-sm leading-6">
      {item.actionId ? (
        <input type="checkbox" checked={!!item.done} disabled={busyId === item.actionId} onChange={(e) => onToggle(item.actionId!, e.target.checked)}
          aria-label={en ? "Mark done" : "শেষ হিসেবে রাখুন"} className="mt-1 h-5 w-5 shrink-0 accent-accent" />
      ) : <span aria-hidden="true" className="mt-2 h-2 w-2 shrink-0 rounded-full bg-warn" />}
      <span className={`min-w-0 flex-1 ${item.done ? "text-muted line-through" : "text-ink"}`}>
        {item.text}
        {item.who && <span className="ml-2 inline-flex rounded-full bg-bg px-2 py-0.5 text-xs text-muted">{strings.casePage.who[item.who as keyof typeof strings.casePage.who] || item.who}</span>}
        {item.step && <button type="button" onClick={() => onGoToStep(item.step!)} className="ml-2 text-xs font-semibold text-accent underline underline-offset-2">{en ? `Open step ${item.step}` : `ধাপ ${bnDigits(item.step)} খুলুন`}</button>}
      </span>
    </li>
  );

  return (
    <section data-tour="next" aria-labelledby="next-title" className="rounded-[var(--radius-card)] border border-accent/20 bg-gradient-to-br from-accent-soft/80 to-surface p-4">
      <h2 id="next-title" className="font-heading text-lg font-bold text-ink">{en ? "What to do now" : "এখন কী করবেন"}</h2>
      {top.length ? <ol className="mt-2 space-y-1">{top.map(row)}</ol>
        : <p className="mt-1 text-sm leading-6 text-muted">{en ? "No open tasks. Add papers and cross-check them to see the next tasks here." : "এখন কোনো খোলা কাজ নেই। কাগজ যোগ করে মিলিয়ে দেখলে এখানে পরের কাজ দেখাবে।"}</p>}
      {rest.length > 0 && (
        <details className="mt-2">
          <summary className="inline-flex min-h-11 cursor-pointer items-center text-sm font-semibold text-accent underline underline-offset-4">{en ? `All tasks (${items.length})` : `সব কাজ (${bnDigits(items.length)})`}</summary>
          <ol className="mt-1 space-y-1">{rest.map(row)}</ol>
        </details>
      )}
    </section>
  );
}
