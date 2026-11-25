"use client";

import React from "react";
import { Card } from "./Card";
import { useLang } from "@/lib/lang";

const labels = { bad: "বড় অমিল", warn: "যাচাই দরকার", ok: "মিলেছে", info: "তথ্য কম" } as const;
const labelsEn = { bad: "Major mismatch", warn: "Needs review", ok: "Matched", info: "Not enough data" } as const;
const pill = {
  bad: "border-bad/30 bg-bad-bg text-bad",
  warn: "border-warn/30 bg-warn-bg text-warn",
  ok: "border-ok/30 bg-ok-bg text-ok",
  info: "border-line bg-bg text-muted",
} as const;
const mark = { bad: "!", warn: "!", ok: "✓", info: "i" } as const;

export type FindingTone = keyof typeof labels;

export const findingTone = (status?: string | null): FindingTone =>
  status === "bad" || status === "warn" || status === "ok" ? status : "info";

export function TonePill({ tone, children }: { tone: FindingTone; children?: React.ReactNode }) {
  const en = useLang() === "en";
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${pill[tone]}`}>
      <span aria-hidden="true" className="inline-flex h-4 w-4 items-center justify-center rounded-full bg-current/15 text-[10px] leading-none">{mark[tone]}</span>
      {children ?? (en ? labelsEn : labels)[tone]}
    </span>
  );
}

/** One card style for every finding on the case page (documents and satellite). */
export function FindingCard({ tone, title, children, footer }: { tone: FindingTone; title: string; children: React.ReactNode; footer?: React.ReactNode }) {
  return (
    <Card as="article" variant="highlight" tone={tone} title={title} meta={<TonePill tone={tone} />} footer={footer} className="!p-4">
      {children}
    </Card>
  );
}
