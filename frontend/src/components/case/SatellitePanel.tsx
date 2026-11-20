"use client";

import React, { useEffect, useState } from "react";
import { api, ApiError, PlotGeometry, SatelliteCheckOut, SatelliteTrend } from "@/lib/api";
import PlotMap from "./PlotMap";

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
  const W = 320, H = 140, L = 34, R = 10, T = 12, B = 26;
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
    <figure className="min-w-0 rounded-lg border border-line bg-bg/40 p-2">
      <figcaption className="px-1 text-sm font-semibold">{label} ({unit})</figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full text-accent" role="img" aria-label={`${label}, বছর অনুযায়ী`}>
        {[y0, y1 / 2, y1].map((v) => (
          <g key={v}>
            <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} className="stroke-line" strokeWidth={1} />
            <text x={L - 4} y={y(v) + 4} textAnchor="end" fontSize={10} className="fill-muted">{fmt(v)}</text>
          </g>
        ))}
        {years.map((yr) => <text key={yr} x={x(yr)} y={H - 8} textAnchor="middle" fontSize={10} className="fill-muted">{bn(String(yr).slice(2))}</text>)}
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
      <section className="space-y-2">
        <h3 className="font-semibold">যা দেখা গেছে</h3>
        {findings.length ? findings.map((f) => (
          <article key={f.rule_id} className={`space-y-1 rounded-xl border p-3 ${f.status === "warn" || f.status === "bad" ? "border-warn/40 bg-warn-bg/40" : "border-line bg-bg/40"}`}>
            <h4 className="font-semibold">{f.title_bn}</h4>
            <p className="text-sm leading-relaxed">{f.message_bn}</p>
            {typeof f.values?.next_action_bn === "string" && <p className="text-sm"><strong>এরপর:</strong> {f.values.next_action_bn}</p>}
          </article>
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
    <section className="space-y-3 rounded-xl border border-line bg-surface p-4 sm:p-5" aria-labelledby="satellite-title">
      <div className="space-y-1">
        <h2 id="satellite-title" className="font-heading text-lg font-bold">স্যাটেলাইট যাচাই</h2>
        <p className="text-sm leading-relaxed text-muted">মানচিত্রে প্লটের সীমানা আঁকুন। ২০১৯ থেকে প্রতি বছরের ফেব্রুয়ারির (শুকনো মৌসুম) স্যাটেলাইট ছবিতে প্লটের আশেপাশে গাছ ও পানি কেমন বদলেছে তা দেখা হবে।</p>
        <p className="text-sm font-semibold text-warn">ছবির প্রতিটি বিন্দু ১০ মিটার, তাই ফলাফল প্লটের চারপাশের প্রায় ২০০ মিটার এলাকার, প্লটের সীমানার ভেতরের নয়।</p>
      </div>
      <PlotMap landId={landId} geometry={geometry} onSaved={setShape} />
      <div className="flex flex-wrap items-center gap-3">
        <button type="button" onClick={start} disabled={!shape || starting || pending} className="min-h-11 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-60">
          {starting ? "শুরু হচ্ছে…" : pending ? "যাচাই চলছে…" : "স্যাটেলাইট যাচাই করুন"}
        </button>
        {!shape && <span className="text-sm text-muted">আগে সীমানা এঁকে রাখুন।</span>}
        {pending && <span role="status" className="text-sm text-muted">সাত বছরের ছবি দেখতে কয়েক মিনিট লাগে। এই পাতা খোলা রাখুন।</span>}
        {check && !pending && <span className="text-xs text-muted">শেষ যাচাই: {new Date(check.created_at).toLocaleString("bn-BD")}</span>}
      </div>
      {error && <p role="alert" className="rounded-lg border border-bad/40 bg-bad-bg p-3 text-sm">{error}</p>}
      {check?.status === "failed" && <p role="alert" className="rounded-lg border border-bad/40 bg-bad-bg p-3 text-sm">{check.error || "যাচাই করা যায়নি।"}</p>}
      {check?.status === "ok" && check.result && <SatelliteResults check={check} />}
      {check?.status === "ok" && <p className="rounded-lg bg-bg p-3 text-xs leading-relaxed text-muted">{check.area_note_bn} স্যাটেলাইট যাচাই কাগজের পরীক্ষার ঝুঁকির মাত্রা বদলায় না।</p>}
    </section>
  );
}
