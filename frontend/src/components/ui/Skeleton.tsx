import React from "react";

export function Skeleton({ className = "" }: { className?: string }) {
  return <span aria-hidden="true" className={`skeleton block ${className}`} />;
}

/** Card-shaped placeholders for lists. */
export function ListSkeleton({ rows = 4, className = "grid gap-3 sm:grid-cols-2" }: { rows?: number; className?: string }) {
  return (
    <div role="status" aria-label="লোড হচ্ছে" className={className}>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="space-y-3 rounded-[var(--radius-card)] border border-edge bg-surface p-4 shadow-rest">
          <Skeleton className="h-5 w-2/3" />
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-9 w-28" />
        </div>
      ))}
    </div>
  );
}

/** Placeholder with the case page's shape: header, tracker, verdict, findings. */
export function CaseSkeleton() {
  return (
    <div role="status" aria-label="কেস লোড হচ্ছে" className="mx-auto max-w-6xl space-y-6 py-4">
      <div className="space-y-2"><Skeleton className="h-8 w-72 max-w-full" /><Skeleton className="h-4 w-48" /></div>
      <div className="rounded-[var(--radius-card)] border border-edge bg-surface p-5 shadow-rest">
        <Skeleton className="h-6 w-40" />
        <div className="mt-5 grid gap-3 md:grid-cols-5">{Array.from({ length: 5 }, (_, i) => <div key={i} className="flex items-center gap-3 md:flex-col"><Skeleton className="h-8 w-8 !rounded-full" /><Skeleton className="h-4 w-24" /></div>)}</div>
        <Skeleton className="mt-5 h-24 w-full" />
      </div>
      <Skeleton className="h-28 w-full !rounded-[var(--radius-card)]" />
      {Array.from({ length: 3 }, (_, i) => <Skeleton key={i} className="h-20 w-full !rounded-[var(--radius-card)]" />)}
    </div>
  );
}
