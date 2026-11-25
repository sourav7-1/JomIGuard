import { useId } from "react";
import { glossaryOf } from "@/lib/glossary";

// A glossary word with a tooltip on hover, keyboard focus or tap (CSS only).
export function Term({ t, children }: { t: string; children?: React.ReactNode }) {
  const id = useId();
  const g = glossaryOf(t);
  if (!g) return <>{children ?? t}</>;
  return (
    <span className="group/term relative inline-block">
      <button type="button" aria-describedby={id} className="cursor-help rounded-sm border-b border-dotted border-accent/60 text-inherit focus-visible:outline-2 focus-visible:outline-accent">
        {children ?? t}
      </button>
      <span role="tooltip" id={id} className="pointer-events-none hidden absolute bottom-full left-1/2 z-30 mb-2 w-64 max-w-[80vw] -translate-x-1/2 rounded-[var(--radius-control)] border border-edge bg-surface p-3 text-left text-xs font-normal leading-5 text-ink shadow-overlay group-focus-within/term:block group-hover/term:block">
        <b>{g.term}</b> <span lang="en" className="text-muted">({g.latin})</span><br />{g.bn}<br /><span lang="en" className="text-muted">{g.en}</span>
      </span>
    </span>
  );
}
