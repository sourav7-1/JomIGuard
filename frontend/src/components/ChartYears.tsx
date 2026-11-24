"use client";

import { useLang } from "@/lib/lang";
import { bnDigits } from "@/lib/digits";

/** Two-digit year labels on an SVG x-axis, in the viewer's language. */
export function ChartYears({ years, y }: { years: (readonly [number, number])[]; y: number }) {
  const en = useLang() === "en";
  return <>{years.map(([yr, x]) => {
    const label = String(yr).slice(2);
    return <text key={yr} x={x} y={y} textAnchor="middle" fontSize={12} className="fill-muted">{en ? label : bnDigits(label)}</text>;
  })}</>;
}
