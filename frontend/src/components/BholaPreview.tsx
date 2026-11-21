import Link from "next/link";
import { BHOLA_CASE } from "@/lib/services";
import { bnDigits } from "@/lib/digits";

// Recorded Bhola demo result (backend/app/scripts/demo_data/satellite_bhola.json), water % per February.
export const BHOLA_WATER = [[2019, 28.1], [2020, 32.1], [2021, 36.2], [2022, 35.7], [2023, 43.9], [2024, 52.5], [2025, 65.0]] as const;
export const bn = bnDigits;

export function BholaPreview() {
  const W = 320, H = 150, L = 8, R = 8, T = 12, B = 26;
  const x = (i: number) => L + (i / (BHOLA_WATER.length - 1)) * (W - L - R);
  const y = (v: number) => T + (1 - v / 70) * (H - T - B);
  const line = BHOLA_WATER.map(([, v], i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const area = `${line} L${x(BHOLA_WATER.length - 1)},${H - B} L${x(0)},${H - B} Z`;
  return (
    <Link href={BHOLA_CASE} className="lift group animate-fade-up relative mx-auto block w-full max-w-md rounded-[var(--radius-card)] border border-edge bg-[var(--glass)] p-5 shadow-raised backdrop-blur-md lg:ml-auto" style={{ ["--i" as string]: 2 }}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold text-sat">স্যাটেলাইট যাচাইয়ের নমুনা</p>
          <p className="mt-0.5 font-heading text-lg font-bold text-ink">ভোলা · চর মেঘনা, দাগ ৪১৭</p>
        </div>
        <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-warn/30 bg-warn-bg px-2.5 py-0.5 text-xs font-semibold text-warn"><span aria-hidden="true">!</span>পানি বাড়ছে</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="mt-3 h-auto w-full text-sat" role="img" aria-label="আশেপাশে পানি, ২০১৯ সালে ২৮ শতাংশ থেকে ২০২৫ সালে ৬৫ শতাংশ">
        <defs>
          <linearGradient id="bhola-fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="currentColor" stopOpacity=".28" /><stop offset="1" stopColor="currentColor" stopOpacity="0" /></linearGradient>
        </defs>
        <path d={area} fill="url(#bhola-fill)" className="[animation:fade-in_900ms_var(--ease)_400ms_both]" />
        <path d={line} fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" pathLength={1} className="[stroke-dasharray:1] [animation:draw-line_1200ms_var(--ease)_200ms_both]" />
        {BHOLA_WATER.map(([yr, v], i) => <circle key={yr} cx={x(i)} cy={y(v)} r={3.5} className="fill-surface [animation:fade-in_300ms_var(--ease)_both]" stroke="currentColor" strokeWidth={2} style={{ animationDelay: `${300 + i * 140}ms` }} />)}
        {BHOLA_WATER.map(([yr], i) => <text key={yr} x={x(i)} y={H - 6} textAnchor="middle" fontSize={12} className="fill-muted">{bn(String(yr).slice(2))}</text>)}
      </svg>
      <p className="mt-2 text-sm leading-6 text-muted">শুকনো মৌসুমে আশেপাশে পানি <b className="text-ink">{bn(28)}%</b> থেকে <b className="text-ink">{bn(65)}%</b>; খতিয়ানে জমি &apos;নাল&apos;।</p>
      <span className="mt-2 inline-flex items-center gap-1 text-sm font-semibold text-sat">কেস খুলুন <span aria-hidden="true" className="transition-transform group-hover:translate-x-1">→</span></span>
    </Link>
  );
}
