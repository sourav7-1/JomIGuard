import React from "react";
import { strings } from "@/lib/strings";

export type CheckItemStatus = "ok" | "warn" | "bad";

export interface CheckItemProps extends React.HTMLAttributes<HTMLDivElement> {
  status: CheckItemStatus;
  title?: string;
  description: string;
  sources?: string[];
}

export function CheckItem({
  status,
  title,
  description,
  sources,
  className = "",
  ...props
}: CheckItemProps) {
  const configs: Record<
    CheckItemStatus,
    { mark: string; bg: string; text: string; label: string }
  > = {
    ok: { mark: "✓", bg: "bg-ok-bg", text: "text-ok", label: strings.status.ok },
    warn: { mark: "?", bg: "bg-warn-bg", text: "text-warn", label: strings.status.warn },
    bad: { mark: "!", bg: "bg-bad-bg", text: "text-bad", label: strings.status.bad },
  };

  const current = configs[status] || configs.ok;

  return (
    <div
      className={`flex items-start gap-3 p-3.5 rounded-xl border border-line bg-surface text-ink transition-colors ${className}`}
      {...props}
    >
      <div
        className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center font-bold text-sm ${current.bg} ${current.text}`}
        aria-label={current.label}
      >
        {current.mark}
      </div>
      <div className="flex-1 min-w-0">
        {title && <div className="font-semibold text-sm mb-0.5">{title}</div>}
        <div className="text-sm leading-relaxed text-ink">{description}</div>
        {sources && sources.length > 0 && (
          <div className="mt-2 text-xs text-muted flex flex-wrap gap-1.5 items-center">
            <span className="font-medium">{strings.labels.sources}:</span>
            {sources.map((s, idx) => (
              <span key={idx} className="bg-bg px-2 py-0.5 rounded border border-line">
                {s}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
