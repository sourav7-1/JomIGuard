"use client";

import React from "react";
import { strings } from "@/lib/strings";
import { stringsEn } from "@/lib/strings-en";
import { useLang } from "@/lib/lang";

export type RiskLevel = "low" | "medium" | "high" | "unknown";

export interface VerdictBoxProps extends React.HTMLAttributes<HTMLDivElement> {
  riskLevel: RiskLevel;
  title?: string;
  summary?: string;
}

const riskConfig: Record<
  RiskLevel,
  {
    border: string;
    bg: string;
    from: string;
    text: string;
    defaultTitle: string;
    defaultSummary: string;
  }
> = {
  low: {
    border: "border-l-ok",
    bg: "bg-ok-bg",
    from: "from-ok-bg",
    text: "text-ok",
    defaultTitle: strings.risk.lowTitle,
    defaultSummary: strings.risk.lowSummary,
  },
  medium: {
    border: "border-l-warn",
    bg: "bg-warn-bg",
    from: "from-warn-bg",
    text: "text-warn",
    defaultTitle: strings.risk.mediumTitle,
    defaultSummary: strings.risk.mediumSummary,
  },
  high: {
    border: "border-l-bad",
    bg: "bg-bad-bg",
    from: "from-bad-bg",
    text: "text-bad",
    defaultTitle: strings.risk.highTitle,
    defaultSummary: strings.risk.highSummary,
  },
  unknown: {
    border: "border-l-line",
    bg: "bg-surface",
    from: "from-bg",
    text: "text-muted",
    defaultTitle: strings.risk.unknownTitle,
    defaultSummary: strings.risk.unknownSummary,
  },
};

export function VerdictBox({
  riskLevel,
  title,
  summary,
  className = "",
  ...props
}: VerdictBoxProps) {
  const en = useLang() === "en";
  const config = riskConfig[riskLevel] || riskConfig.unknown;
  const key = (riskLevel in riskConfig ? riskLevel : "unknown") as RiskLevel;
  const fallbackTitle = en ? stringsEn.risk[`${key}Title` as const] : config.defaultTitle;
  const fallbackSummary = en ? stringsEn.risk[`${key}Summary` as const] : config.defaultSummary;

  return (
    <div
      role="region"
      aria-label={title || fallbackTitle}
      className={`relative overflow-hidden rounded-[var(--radius-card)] border border-edge border-l-4 bg-gradient-to-br to-surface p-5 shadow-raised ${config.border} ${config.from} ${className}`}
      {...props}
    >
      <RiskBadge riskLevel={riskLevel} />
      <h3 className={`mt-3 text-lg md:text-xl font-bold font-heading mb-1.5 ${config.text}`}>
        {title || fallbackTitle}
      </h3>
      <p className="text-sm md:text-base text-ink leading-relaxed">
        {summary || fallbackSummary}
      </p>
    </div>
  );
}

const badge: Record<RiskLevel, { label: string; en: string; cls: string; icon: string }> = {
  high: { label: "উচ্চ ঝুঁকি", en: "High risk", cls: "bg-bad text-surface", icon: "M12 8v5 M12 16.5v.5 M10.3 3.9 2.6 17.5A2 2 0 0 0 4.3 20.5h15.4a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" },
  medium: { label: "মাঝারি ঝুঁকি", en: "Medium risk", cls: "bg-warn text-surface", icon: "M12 8v5 M12 16.5v.5 M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Z" },
  low: { label: "কম ঝুঁকি", en: "Low risk", cls: "bg-ok text-surface", icon: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Z M8.5 12.5l2.5 2.5 4.5-5" },
  unknown: { label: "তথ্য কম", en: "Not enough data", cls: "bg-muted text-surface", icon: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Z M12 11v5 M12 7.5v.5" },
};

/** Risk level as a pill with an icon (never says the land is clear, only the risk level). */
export function RiskBadge({ riskLevel }: { riskLevel: RiskLevel }) {
  const en = useLang() === "en";
  const b = badge[riskLevel] || badge.unknown;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-semibold shadow-rest ${b.cls}`}>
      <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" className="h-4 w-4"><path d={b.icon} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
      {en ? b.en : b.label}
    </span>
  );
}
