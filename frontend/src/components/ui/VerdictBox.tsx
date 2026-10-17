import React from "react";
import { strings } from "@/lib/strings";

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
    text: string;
    defaultTitle: string;
    defaultSummary: string;
  }
> = {
  low: {
    border: "border-ok",
    bg: "bg-ok-bg",
    text: "text-ok",
    defaultTitle: strings.risk.lowTitle,
    defaultSummary: strings.risk.lowSummary,
  },
  medium: {
    border: "border-warn",
    bg: "bg-warn-bg",
    text: "text-warn",
    defaultTitle: strings.risk.mediumTitle,
    defaultSummary: strings.risk.mediumSummary,
  },
  high: {
    border: "border-bad",
    bg: "bg-bad-bg",
    text: "text-bad",
    defaultTitle: strings.risk.highTitle,
    defaultSummary: strings.risk.highSummary,
  },
  unknown: {
    border: "border-line",
    bg: "bg-surface",
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
  const config = riskConfig[riskLevel] || riskConfig.unknown;

  return (
    <div
      role="region"
      aria-label={title || config.defaultTitle}
      className={`rounded-xl border-2 p-5 ${config.border} ${config.bg} ${className}`}
      {...props}
    >
      <h3 className={`text-lg md:text-xl font-bold font-heading mb-1.5 ${config.text}`}>
        {title || config.defaultTitle}
      </h3>
      <p className="text-sm md:text-base text-ink leading-relaxed">
        {summary || config.defaultSummary}
      </p>
    </div>
  );
}
