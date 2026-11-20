"use client";

import React, { useEffect, useState } from "react";
import { api, ApiError, PlotGeometry, SatelliteCheckOut, SatelliteTrend } from "@/lib/api";
import PlotMap from "./PlotMap";
import { FindingCard, findingTone } from "@/components/ui/FindingCard";
import { Spinner } from "@/components/ui/Spinner";

const POLL_MS = 5000;
const BN = "০১২৩৪৫৬৭৮৯";
const bn = (v: number | string) => String(v).replace(/\d/g, (d) => BN[Number(d)]);
const fmt = (v: number) => bn(Number.isInteger(v) ? v : v.toFixed(1));

const METRICS: { key: string; label: string; unit: string }[] = [
  { key: "tree_cover_pct", label: "গাছে ঢাকা জায়গা", unit: "%" },
  { key: "water_pct", label: "পানি", unit: "%" },
];

function MetricChart({ label, unit, trend, outliers }: { label: string; unit: string; trend: SatelliteTrend; outliers: number[] }) {
  const pts = trend.series;
  if (pts.length < 2) return null;
  const W = 340, H = 175, L = 36, R = 12, T = 14, B = 30;
  const years = pts.map((p) => p.year);
  const values = pts.map((p) => p.value);
  const y0 = 0, y1 = Math.max(5, Math.ceil(Math.max(...values) / 5) * 5);
  const x = (yr: number) => L + ((yr - years[0]) / Math.max(1, years[years.length - 1] - years[0])) * (W - L - R);
  const y = (v: number) => T + (1 - (v - y0) / (y1 - y0)) * (H - T - B);
  const flagged = (p: (typeof pts)[number]) => p.low_confidence || outliers.includes(p.year);
  const good = pts.filter((p) => !flagged(p));
  const path = good.map((p, i) => `${i ? "L" : "M"}${x(p.year).toFixed(1)},${y(p.value).toFixed(1)}`).join(" ");
  const why = (p: (typeof pts)[number]) =>
    p.low_confidence ? "কম নির্ভরযোগ্য বছর (ছবি কম বা মান ভালো নয়), প্রবণতায় ধরা হয়নি"
      : outliers.includes(p.year) ? "ব্যতিক্রমী বছর (এক বছরের অস্বাভাবিক ছবি), প্রবণতায় ধরা হয়নি" : "প্রবণতায় ধরা হয়েছে";
  return (
    <figure className="min-w-0 rounded-[var(--radius-card)] border border-line bg-surface p-3">
      <figcaption className="px-1 text-sm font-semibold text-ink">{label} ({unit})</figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} className="mx-auto h-auto w-full max-w-sm text-sat" role="img" aria-label={`${label}, বছর অনুযায়ী`}>
        {[y0, y1 / 2, y1].map((v) => (
          <g key={v}>
            <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} className="stroke-line" strokeWidth={1} />
            <text x={L - 5} y={y(v) + 4} textAnchor="end" fontSize={14} className="fill-muted">{fmt(v)}</text>
          </g>
        ))}
        {years.map((yr) => <text key={yr} x={x(yr)} y={H - 8} textAnchor="middle" fontSize={14} className="fill-muted">{bn(String(yr).slice(2))}</text>)}
        <path d={path} fill="none" stroke="currentColor" strokeWidth={2} />
        {pts.map((p) => (
          <circle key={p.year} cx={x(p.year)} cy={y(p.value)} r={flagged(p) ? 4.5 : 3.5} strokeWidth={2}
            stroke="currentColor" className={flagged(p) ? "fill-surface" : "fill-current"}>
            <title>{`${bn(p.year)}: ${fmt(p.value)}${unit} — ${why(p)}`}</title>
          </circle>
        ))}
      </svg>
    </figure>
  );
}

function SatelliteResults({ check }: { check: SatelliteCheckOut }) {
  const r = check.result!;
  const findings = check.findings ?? [];
  return (
    <div className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-2">
        {METRICS.map((m) => {
          const trend = r.trends[m.key];
          return trend ? <MetricChart key={m.key} label={m.label} unit={m.unit} trend={trend} outliers={trend.outlier_years} /> : null;
        })}
      </div>
      <p className="text-xs text-muted">ভরাট বিন্দু: প্রবণতায় ধরা বছর। ফাঁপা বিন্দু: ব্যতিক্রমী বা কম নির্ভরযোগ্য বছর (বিন্দুর ওপর মাউস রাখলে কারণ দেখাবে)।</p>
      <section className="space-y-3">
        <h3 className="font-heading text-lg font-bold text-ink">যা দেখা গেছে</h3>
        {findings.length ? findings.map((f) => (
          <FindingCard key={f.rule_id} tone={findingTone(f.status)} title={f.title_bn}>
            <p className="text-sm leading-relaxed">{f.message_bn}</p>
            {typeof f.values?.next_action_bn === "string" && <p className="text-sm leading-relaxed"><strong>এরপর:</strong> {f.values.next_action_bn}</p>}
          </FindingCard>
        )) : <p className="rounded-xl border border-line bg-bg/40 p-3 text-sm text-muted">স্যাটেলাইট ছবিতে আশেপাশে সতর্ক হওয়ার মতো কোনো পরিবর্তন ধরা পড়েনি। এর মানে এই নয় যে জমিতে কোনো সমস্যা নেই; মাঠে গিয়ে নিজে দেখুন।</p>}
      </section>
    </div>
  );
}

export function SatellitePanel({ landId, geometry }: { landId: string; geometry: PlotGeometry | null }) {
  const [shape, setShape] = useState(geometry);
  const [check, setCheck] = useState<SatelliteCheckOut | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0); // bump to fetch the latest check again

  useEffect(() => {
    let cancelled = false;
    let timer: number | undefined;
    api.getLatestSatelliteCheck(landId).then((latest) => {
      if (cancelled) return;
      setCheck(latest);
      if (latest.status === "pending") timer = window.setTimeout(() => setTick((t) => t + 1), POLL_MS);
    }).catch((e) => {
      if (!cancelled && !(e instanceof ApiError && e.status === 404)) setError(e instanceof Error ? e.message : "ফল আনা যায়নি।");
    });
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [landId, tick]);

  const start = async () => {
    setStarting(true);
    setError(null);
    try {
      setCheck(await api.startSatelliteCheck(landId));
      setTick((t) => t + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : "যাচাই শুরু করা যায়নি।");
    } finally {
      setStarting(false);
    }
  };

  const pending = check?.status === "pending";
  return (
    <section className="space-y-4 rounded-[var(--radius-card)] border border-line border-t-4 border-t-sat bg-surface p-4 shadow-[var(--shadow-card)] sm:p-5" aria-labelledby="satellite-title">
      <div className="space-y-2">
        <p className="inline-flex items-center gap-2 rounded-full bg-sat-soft px-3 py-1 text-xs font-semibold text-sat">
          <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" className="h-4 w-4"><path d="M4 12a8 8 0 0 1 8-8m-5 8a5 5 0 0 1 5-5m-1 8 7-7m-4 0h4v4M10 18l-2 2m6-6 6 6-2 2-6-6" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></svg>
          মাঠের ছবি
        </p>
        <h2 id="satellite-title" className="scroll-mt-40 font-heading text-xl font-bold text-ink">স্যাটেলাইট যাচাই</h2>
        <p className="text-sm leading-relaxed text-muted">মানচিত্রে প্লটের সীমানা আঁকুন। ২০১৯ থেকে প্রতি বছরের ফেব্রুয়ারির (শুকনো মৌসুম) স্যাটেলাইট ছবিতে প্লটের আশেপাশে গাছ ও পানি কেমন বদলেছে তা দেখা হবে।</p>
        <p className="flex items-start gap-2 text-xs leading-relaxed text-muted">
          <span aria-hidden="true" className="mt-0.5 inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-muted text-[10px] font-bold">i</span>
          ছবির প্রতিটি বিন্দু ১০ মিটার, তাই ফলাফল প্লটের চারপাশের প্রায় ২০০ মিটার এলাকার, প্লটের সীমানার ভেতরের নয়।
        </p>
      </div>
      <div className="-mx-4 sm:mx-0">
        <PlotMap landId={landId} geometry={geometry} onSaved={setShape} />
      </div>
      {!shape && (
        <div className="rounded-[var(--radius-card)] border border-dashed border-line bg-bg/60 p-4 text-sm leading-relaxed">
          <p className="font-semibold text-ink">এখনো সীমানা আঁকা হয়নি</p>
          <ol className="mt-1 list-decimal space-y-0.5 pl-5 text-muted">
            <li>মানচিত্রের ডান দিকের বহুভুজ বোতাম চাপুন।</li>
            <li>প্লটের প্রতিটি কোণে একবার করে ক্লিক করুন, শেষে প্রথম বিন্দুতে ক্লিক করুন।</li>
            <li>“সীমানা রাখুন” চাপুন, তারপর স্যাটেলাইট যাচাই শুরু করুন।</li>
          </ol>
        </div>
      )}
      <div className="flex flex-wrap items-center gap-3">
        <button type="button" onClick={start} disabled={!shape || starting || pending} className="min-h-11 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white">
          {starting ? "শুরু হচ্ছে…" : pending ? "যাচাই চলছে…" : "স্যাটেলাইট যাচাই করুন"}
        </button>
        {check && !pending && <span className="text-xs text-muted">শেষ যাচাই: {new Date(check.created_at).toLocaleString("bn-BD")}</span>}
      </div>
      {(pending || starting) && (
        <div role="status" aria-live="polite" className="flex items-start gap-3 rounded-[var(--radius-card)] border border-sat/30 bg-sat-soft p-4 text-sm">
          <Spinner size="sm" />
          <div className="space-y-1">
            <p className="font-semibold text-ink">স্যাটেলাইট ছবি দেখা হচ্ছে…</p>
            <p className="leading-relaxed text-muted">২০১৯ থেকে ২০২৫ পর্যন্ত সাত বছরের ছবি দেখতে সাধারণত এক থেকে কয়েক মিনিট লাগে। এই পাতা খোলা রাখুন, ফল এলে এখানেই দেখাবে।</p>
          </div>
        </div>
      )}
      {error && <p role="alert" className="rounded-lg border border-bad/40 bg-bad-bg p-3 text-sm">{error}</p>}
      {check?.status === "failed" && <p role="alert" className="rounded-lg border border-bad/40 bg-bad-bg p-3 text-sm">{check.error || "যাচাই করা যায়নি।"}</p>}
      {check?.status === "ok" && check.result && <SatelliteResults check={check} />}
      {check?.status === "ok" && <p className="rounded-lg bg-bg p-3 text-xs leading-relaxed text-muted">{check.area_note_bn} স্যাটেলাইট যাচাই কাগজের পরীক্ষার ঝুঁকির মাত্রা বদলায় না।</p>}
    </section>
  );
}
