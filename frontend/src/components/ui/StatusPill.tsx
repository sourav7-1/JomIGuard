import React from "react";
import { Badge, type BadgeVariant } from "./Badge";
import { strings } from "@/lib/strings";

export type DocumentStatus =
  | "uploaded"
  | "queued"
  | "processing"
  | "done"
  | "failed"
  | "needs_review";

export interface StatusPillProps {
  status: DocumentStatus;
  label?: string;
  className?: string;
}

const statusMap: Record<DocumentStatus, { variant: BadgeVariant; defaultLabel: string }> = {
  uploaded: { variant: "neutral", defaultLabel: strings.status.uploaded },
  queued: { variant: "neutral", defaultLabel: strings.status.queued },
  processing: { variant: "warn", defaultLabel: strings.status.processing },
  done: { variant: "ok", defaultLabel: strings.status.done },
  failed: { variant: "bad", defaultLabel: strings.status.failed },
  needs_review: { variant: "warn", defaultLabel: strings.status.needs_review },
};

export function StatusPill({ status, label, className }: StatusPillProps) {
  const item = statusMap[status] || statusMap.uploaded;
  return (
    <Badge variant={item.variant} className={className}>
      <span className="w-1.5 h-1.5 rounded-full bg-current" aria-hidden="true" />
      {label || item.defaultLabel}
    </Badge>
  );
}
