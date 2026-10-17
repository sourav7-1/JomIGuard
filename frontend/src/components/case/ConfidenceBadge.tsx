"use client";

import React, { useState } from "react";
import { strings } from "@/lib/strings";

interface ConfidenceBadgeProps {
  flags?: string[] | string;
  className?: string;
}

export function ConfidenceBadge({ flags, className = "" }: ConfidenceBadgeProps) {
  const [showTooltip, setShowTooltip] = useState(false);

  const flagList: string[] = Array.isArray(flags)
    ? flags
    : typeof flags === "string"
      ? [flags]
      : [];

  if (flagList.length === 0) {
    return null;
  }

  const isHuman = flagList.some((f) => f.toLowerCase() === "human");
  const isLow = flagList.some((f) => f.toLowerCase() === "low");
  const isMedium = flagList.some((f) => f.toLowerCase() === "medium");

  const nonConfidenceFlags = flagList.filter(
    (f) => !["human", "low", "medium", "high"].includes(f.toLowerCase())
  );

  const getReasonText = (code: string) => {
    switch (code) {
      case "unsupported_unit":
        return strings.casePage.unsupportedUnitReason;
      case "missing_unit":
        return strings.casePage.missingUnitReason;
      case "unparseable_number":
        return strings.casePage.unparseableNumberReason;
      case "unparseable_date":
        return strings.casePage.unparseableDateReason;
      default:
        return code;
    }
  };

  if (isHuman) {
    return (
      <span
        title={strings.casePage.confidenceHuman}
        className={`inline-flex items-center text-ok font-bold text-xs ${className}`}
      >
        <span className="inline-block mr-0.5">✓</span>
      </span>
    );
  }

  const level = isLow ? "low" : isMedium ? "medium" : null;
  if (!level && nonConfidenceFlags.length === 0) {
    return null;
  }

  const badgeText = isLow
    ? strings.casePage.confidenceLow
    : isMedium
      ? strings.casePage.confidenceMedium
      : nonConfidenceFlags.length > 0
        ? getReasonText(nonConfidenceFlags[0])
        : "";

  const colorClass = isLow
    ? "bg-bad-bg/60 text-bad border-bad/30"
    : "bg-warn-bg/60 text-warn border-warn/30";

  return (
    <div className={`relative inline-block ${className}`}>
      <button
        type="button"
        onClick={() => setShowTooltip(!showTooltip)}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        className={`text-[11px] font-medium px-1.5 py-0.5 rounded border ${colorClass} cursor-help transition-opacity hover:opacity-90`}
      >
        {isLow ? "!" : "?"} {badgeText}
      </button>

      {showTooltip && (
        <div className="absolute z-30 bottom-full left-0 mb-1.5 w-64 p-2 text-xs bg-ink text-surface rounded-lg shadow-lg border border-line pointer-events-none">
          <div className="font-semibold mb-1 text-[11px]">
            {isLow ? strings.casePage.confidenceLow : strings.casePage.confidenceMedium}
          </div>
          {nonConfidenceFlags.length > 0 ? (
            <ul className="list-disc list-inside space-y-0.5 text-[11px]">
              {nonConfidenceFlags.map((flag, idx) => (
                <li key={idx}>{getReasonText(flag)}</li>
              ))}
            </ul>
          ) : (
            <div className="text-[11px] text-surface/80">
              কাগজের এই লেখাটি অস্পষ্ট হওয়ায় AI কম নিশ্চয়তায় তথ্যটি পড়েছে। অনুগ্রহ করে মূল কাগজের সাথে মিলিয়ে নিন।
            </div>
          )}
        </div>
      )}
    </div>
  );
}
