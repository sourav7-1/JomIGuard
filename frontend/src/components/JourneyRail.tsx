"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { strings } from "@/lib/strings";

interface StepItem {
  id: string;
  stepNo: string;
  label: string;
  desc: string;
  href: string;
  isActive: (pathname: string) => boolean;
}

const steps: StepItem[] = [
  {
    id: "step1",
    stepNo: "ধাপ ১",
    label: strings.nav.step1Short,
    desc: strings.nav.step1Desc,
    href: "/cases",
    isActive: (p) => (p.startsWith("/cases") && !p.includes("/timeline")) || p.startsWith("/upload"),
  },
  {
    id: "step2",
    stepNo: "ধাপ ২",
    label: strings.nav.step2Short,
    desc: strings.nav.step2Desc,
    href: "/cases/demo/timeline",
    isActive: (p) => p.includes("/timeline"),
  },
  {
    id: "step3",
    stepNo: "ধাপ ৩",
    label: strings.nav.step3Short,
    desc: strings.nav.step3Desc,
    href: "/escrow",
    isActive: (p) => p.startsWith("/escrow"),
  },
  {
    id: "step4",
    stepNo: "ধাপ ৪",
    label: strings.nav.step4Short,
    desc: strings.nav.step4Desc,
    href: "/guardian",
    isActive: (p) => p.startsWith("/guardian"),
  },
];

export function JourneyRail() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="সেবা ধাপসমূহ"
      className="w-full max-w-5xl mx-auto px-4 py-3"
    >
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 md:gap-3">
        {steps.map((step) => {
          const active = step.isActive(pathname);
          return (
            <Link
              key={step.id}
              href={step.href}
              className={`min-h-[56px] p-2.5 md:p-3 rounded-xl border transition-all flex flex-col justify-center text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent select-none ${
                active
                  ? "bg-accent-soft border-accent text-accent shadow-xs font-semibold"
                  : "bg-surface border-line text-ink hover:border-accent/40 hover:bg-surface/80"
              }`}
            >
              <div className="flex items-center gap-1.5 text-xs font-bold">
                <span
                  className={`px-1.5 py-0.5 rounded text-[11px] ${
                    active ? "bg-accent text-white" : "bg-bg text-muted border border-line"
                  }`}
                >
                  {step.stepNo}
                </span>
                <span className="truncate">{step.label}</span>
              </div>
              <div className="hidden sm:block text-[11px] text-muted truncate mt-1">
                {step.desc}
              </div>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
