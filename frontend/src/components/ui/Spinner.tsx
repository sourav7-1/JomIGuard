import React from "react";
import { strings } from "@/lib/strings";

export interface SpinnerProps {
  size?: "sm" | "md" | "lg";
  label?: string;
  className?: string;
}

export function Spinner({
  size = "md",
  label = strings.labels.loading,
  className = "",
}: SpinnerProps) {
  const sizes = {
    sm: "w-4 h-4 border-2",
    md: "w-6 h-6 border-2",
    lg: "w-10 h-10 border-3",
  };

  return (
    <div
      role="status"
      aria-label={label}
      className={`inline-flex items-center justify-center ${className}`}
    >
      <div
        className={`animate-spin rounded-full border-line border-t-accent ${sizes[size]}`}
      />
      <span className="sr-only">{label}</span>
    </div>
  );
}
