import React from "react";

export type BadgeVariant = "ok" | "warn" | "bad" | "neutral";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

export function Badge({
  variant = "neutral",
  className = "",
  children,
  ...props
}: BadgeProps) {
  const variants: Record<BadgeVariant, string> = {
    ok: "bg-ok-bg text-ok border-ok/30",
    warn: "bg-warn-bg text-warn border-warn/30",
    bad: "bg-bad-bg text-bad border-bad/30",
    neutral: "bg-surface text-muted border-line",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-full border ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </span>
  );
}
