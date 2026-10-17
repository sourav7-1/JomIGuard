import React from "react";

export interface ChecklistItem {
  id: string;
  label: string;
  checked?: boolean;
}

export interface ChecklistProps {
  items: ChecklistItem[];
  onToggle?: (id: string, checked: boolean) => void;
  className?: string;
}

export function Checklist({ items, onToggle, className = "" }: ChecklistProps) {
  return (
    <ul className={`space-y-2.5 ${className}`}>
      {items.map((item) => (
        <li key={item.id} className="min-h-[44px] flex items-center">
          <label className="flex items-start gap-3 w-full cursor-pointer py-2 px-1 select-none rounded-lg hover:bg-surface/60 transition-colors">
            <input
              type="checkbox"
              checked={item.checked ?? false}
              onChange={(e) => onToggle?.(item.id, e.target.checked)}
              className="mt-0.5 w-5 h-5 rounded border-line text-accent accent-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent cursor-pointer"
            />
            <span
              className={`text-sm md:text-base leading-relaxed ${
                item.checked ? "line-through text-muted" : "text-ink"
              }`}
            >
              {item.label}
            </span>
          </label>
        </li>
      ))}
    </ul>
  );
}
