"use client";

import React, { useEffect, useRef } from "react";
import { bnDigits } from "@/lib/digits";
import { useLang } from "@/lib/lang";
import { PHASE_LABELS, STATUS_LABELS, STEP_LABELS, type JourneyStep, type Phase, type StepKey } from "@/lib/journey";

const DOT: Record<JourneyStep["status"], string> = {
  done: "border-ok bg-ok text-white",
  action: "border-warn bg-warn-bg text-warn",
  waiting: "border-sat bg-sat-soft text-sat",
  locked: "border-line bg-bg text-muted",
  todo: "border-line bg-surface text-muted",
};
const MARK: Record<JourneyStep["status"], string> = { done: "✓", action: "!", waiting: "…", locked: "🔒", todo: "" };

/** Sticky row of the 8 journey steps in 3 phases; picking one shows its panel. */
export function JourneyStepper({ steps, active, onSelect }: { steps: JourneyStep[]; active: number; onSelect: (n: number) => void }) {
  const en = useLang() === "en";
  const num = (v: number) => (en ? String(v) : bnDigits(v));
  const rowRef = useRef<HTMLDivElement>(null);

  // keep the active chip in view on phones (the row scrolls sideways)
  useEffect(() => {
    rowRef.current?.querySelector<HTMLElement>(`[data-step="${active}"]`)?.scrollIntoView({ block: "nearest", inline: "center" });
  }, [active]);

  const phases: Phase[] = ["before", "during", "after"];
  return (
    <nav data-tour="stepper" aria-label={en ? "Steps for this plot" : "এই জমির ধাপ"} className="sticky top-[var(--header-h,0px)] z-30 -mx-4 border-y border-edge bg-[var(--glass)] px-4 py-2 backdrop-blur-xl sm:mx-0 sm:rounded-[var(--radius-card)] sm:border sm:shadow-rest">
      <div ref={rowRef} className="flex gap-3 overflow-x-auto pb-1 [scrollbar-width:thin]">
        {phases.map((phase) => (
          <div key={phase} className="flex shrink-0 flex-col gap-1">
            <p className="px-1 text-[11px] font-semibold uppercase tracking-wide text-muted">{en ? PHASE_LABELS[phase].en : PHASE_LABELS[phase].bn}</p>
            <ol className="flex gap-1">
              {steps.filter((s) => s.phase === phase).map((s) => {
                const label = STEP_LABELS[s.key as StepKey];
                const isActive = s.n === active;
                return (
                  <li key={s.n}>
                    <button type="button" data-step={s.n} onClick={() => onSelect(s.n)} aria-current={isActive ? "step" : undefined}
                      aria-label={`${num(s.n)}. ${en ? label.en : label.bn}: ${en ? STATUS_LABELS[s.status].en : STATUS_LABELS[s.status].bn}`}
                      className={`flex min-h-11 items-center gap-2 rounded-[var(--radius-control)] border px-2 py-1 text-left transition-colors focus-visible:outline-2 focus-visible:outline-accent ${isActive ? "border-accent bg-accent-soft" : "border-transparent hover:bg-bg"}`}>
                      <span aria-hidden="true" className={`inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 text-xs font-bold ${DOT[s.status]}`}>{MARK[s.status]}</span>
                      <span className="whitespace-nowrap">
                        <span className={`block text-xs font-semibold leading-tight ${isActive ? "text-accent" : "text-ink"}`}>{num(s.n)}. {en ? label.en : label.bn}</span>
                        <span className="block text-[11px] leading-tight text-muted">{en ? STATUS_LABELS[s.status].en : STATUS_LABELS[s.status].bn}</span>
                      </span>
                    </button>
                  </li>
                );
              })}
            </ol>
          </div>
        ))}
      </div>
    </nav>
  );
}
