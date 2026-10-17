import React from "react";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  as?: "div" | "section" | "article";
  variant?: "surface" | "soft";
}

export function Card({
  as: Component = "div",
  variant = "surface",
  className = "",
  children,
  ...props
}: CardProps) {
  const variants = {
    surface: "bg-surface text-ink border border-line shadow-xs",
    soft: "bg-accent-soft text-ink border border-line/60",
  };

  return (
    <Component
      className={`rounded-xl p-5 ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </Component>
  );
}

export const Box = Card;
