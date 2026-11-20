import React from "react";

const tones = {
  bad: "border-l-bad bg-bad-bg/40",
  warn: "border-l-warn bg-warn-bg/50",
  ok: "border-l-ok bg-ok-bg/50",
  info: "border-l-line bg-bg/60",
} as const;

const labels = { bad: "বড় অমিল", warn: "যাচাই দরকার", ok: "মিলেছে", info: "তথ্য কম" } as const;

export type FindingTone = keyof typeof tones;

export const findingTone = (status?: string | null): FindingTone =>
  status === "bad" || status === "warn" || status === "ok" ? status : "info";

/** One card style for every finding on the case page (documents and satellite). */
export function FindingCard({ tone, title, children }: { tone: FindingTone; title: string; children: React.ReactNode }) {
  return (
    <article className={`space-y-2 rounded-[var(--radius-card)] border border-line border-l-4 p-4 ${tones[tone]}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 className="font-semibold leading-snug text-ink">{title}</h3>
        <span className="shrink-0 rounded-full border border-line bg-surface px-2 py-0.5 text-xs font-medium text-muted">{labels[tone]}</span>
      </div>
      {children}
    </article>
  );
}
