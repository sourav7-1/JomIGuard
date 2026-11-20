import React from "react";
import Link from "next/link";

export type CardTone = "bad" | "warn" | "ok" | "info";
export type CardVariant = "default" | "interactive" | "highlight" | "satellite" | "glass" | "surface" | "soft";

export interface CardProps extends Omit<React.HTMLAttributes<HTMLElement>, "title"> {
  as?: "div" | "section" | "article" | "li";
  variant?: CardVariant;
  /** highlight variant: coloured left border for findings */
  tone?: CardTone;
  /** interactive variant: the whole card links here (stretched link on the title) */
  href?: string;
  icon?: React.ReactNode;
  title?: React.ReactNode;
  titleAs?: "h2" | "h3" | "h4";
  description?: React.ReactNode;
  meta?: React.ReactNode;
  footer?: React.ReactNode;
  padded?: boolean;
}

const base = "relative rounded-[var(--radius-card)] border text-ink";
const variants: Record<CardVariant, string> = {
  default: "surface-grad border-edge bg-surface shadow-rest",
  surface: "surface-grad border-edge bg-surface shadow-rest",
  soft: "border-edge bg-accent-soft",
  interactive: "lift surface-grad border-edge bg-surface shadow-rest hover:border-accent/40 has-[a[data-stretched]:focus-visible]:ring-2 has-[a[data-stretched]:focus-visible]:ring-accent has-[a[data-stretched]:focus-visible]:ring-offset-2 has-[a[data-stretched]:focus-visible]:ring-offset-bg",
  highlight: "border-edge border-l-4 bg-surface shadow-rest",
  satellite: "surface-grad border-sat/30 bg-surface shadow-rest before:absolute before:inset-x-4 before:top-0 before:h-0.5 before:rounded-full before:bg-gradient-to-r before:from-sat before:to-accent",
  glass: "border-edge bg-[var(--glass)] shadow-raised backdrop-blur-md",
};
const tones: Record<CardTone, string> = {
  bad: "border-l-bad bg-gradient-to-r from-bad-bg/70 to-surface",
  warn: "border-l-warn bg-gradient-to-r from-warn-bg/80 to-surface",
  ok: "border-l-ok bg-gradient-to-r from-ok-bg/70 to-surface",
  info: "border-l-line bg-gradient-to-r from-bg to-surface",
};

/** One card for the whole app. Slots: icon, title, description, meta, children, footer. */
export function Card({
  as: Component = "div",
  variant = "default",
  tone = "info",
  href,
  icon,
  title,
  titleAs: Title = "h3",
  description,
  meta,
  footer,
  padded = true,
  className = "",
  children,
  ...props
}: CardProps) {
  const slots = icon || title || description || meta;
  return (
    <Component
      className={`${base} ${variants[variant]} ${variant === "highlight" ? tones[tone] : ""} ${padded && !/(^|\s)p-\d/.test(className) ? "p-4 sm:p-5" : ""} ${className}`}
      {...props}
    >
      {slots && (
        <div className="flex items-start gap-3">
          {icon}
          <div className="min-w-0 flex-1 space-y-1">
            {(title || meta) && (
              <div className="flex flex-wrap items-start justify-between gap-2">
                {title && (
                  <Title className="font-heading text-lg font-bold leading-snug text-ink">
                    {href ? (
                      <Link href={href} data-stretched className="outline-none after:absolute after:inset-0 after:rounded-[var(--radius-card)] after:content-['']">
                        {title}
                      </Link>
                    ) : title}
                  </Title>
                )}
                {meta && <div className="shrink-0">{meta}</div>}
              </div>
            )}
            {description && <div className="text-sm leading-7 text-muted">{description}</div>}
          </div>
        </div>
      )}
      {slots ? children && <div className="mt-3 space-y-3">{children}</div> : children}
      {footer && <div className="relative z-10 mt-4 flex flex-wrap items-center gap-2">{footer}</div>}
    </Component>
  );
}

/** Soft gradient tile for card icons. */
export function IconTile({ children, satellite = false, className = "" }: { children: React.ReactNode; satellite?: boolean; className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={`inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-[var(--radius-control)] border border-edge bg-gradient-to-br shadow-rest ${
        satellite ? "from-sat-soft to-surface text-sat" : "from-accent-soft to-surface text-accent"
      } ${className}`}
    >
      {children}
    </span>
  );
}

export const Box = Card;
