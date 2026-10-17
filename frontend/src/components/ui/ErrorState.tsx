import React from "react";
import { Button } from "./Button";
import { strings } from "@/lib/strings";

export interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({
  title = strings.error.defaultTitle,
  message = strings.error.defaultMessage,
  onRetry,
  className = "",
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={`rounded-xl border border-bad/30 bg-bad-bg p-5 text-ink ${className}`}
    >
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-bad text-white flex items-center justify-center font-bold text-sm">
          !
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="text-base font-bold text-bad mb-1">{title}</h4>
          <p className="text-sm text-ink mb-3 leading-relaxed">{message}</p>
          {onRetry && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onRetry}
              className="bg-surface border-line text-ink"
            >
              {strings.buttons.retry}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
