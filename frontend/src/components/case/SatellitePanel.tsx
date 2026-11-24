"use client";

import React, { useEffect, useState } from "react";
import { api, ApiError, PlotGeometry, SatelliteCheckOut, SatelliteTrend } from "@/lib/api";
import PlotMap from "./PlotMap";
import { FindingCard, findingTone, TonePill } from "@/components/ui/FindingCard";
import { Spinner } from "@/components/ui/Spinner";
import { Skeleton } from "@/components/ui/Skeleton";
import { Modal } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";
import { RuleResultOut } from "@/lib/api";
import { bnDigits } from "@/lib/digits";
import { useLang } from "@/lib/lang";

const POLL_MS = 5000;
const LOAD_ERROR = "__load__";
const fmtNum = (v: number) => (Number.isInteger(v) ? String(v) : v.toFixed(1));

const METRICS: { key: string; label: string; labelEn: string; unit: string }[] = [
  { key: "tree_cover_pct", label: "গাছে ঢাকা জায়গা", labelEn: "Tree cover", unit: "%" },
  { key: "water_pct", label: "পানি", labelEn: "Water", unit: "%" },
];

function MetricChart({ label, unit, trend, outliers }: { label: string; unit: string; trend: SatelliteTrend; outliers: number[] }) {
  const en = useLang() === "en";
  const t = (b: string, e: string) => (en ? e : b);
  const bn = (v: number | string) => (en ? String(v) : bnDigits(v));
  const fmt = (v: number) => bn(fmtNum(v));
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
    p.low_confidence ? t("কম নির্ভরযোগ্য বছর (ছবি কম বা মান ভালো নয়), প্রবণতায় ধরা হয়নি", "Low-confidence year (few or poor images), left out of the trend")
      : outliers.includes(p.year) ? t("ব্যতিক্রমী বছর (এক বছরের অস্বাভাবিক ছবি), প্রবণতায় ধরা হয়নি", "Outlier year (one unusual year of images), left out of the trend") : t("প্রবণতায় ধরা হয়েছে", "Counted in the trend");
  return (
    <figure className="min-w-0 rounded-[var(--radius-card)] border border-edge bg-surface p-3 shadow-rest">
      <figcaption className="px-1 text-sm font-semibold text-ink">{label} ({unit})</figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} className="mx-auto h-auto w-full max-w-sm text-sat" role="img" aria-label={`${label}, ${t("বছর অনুযায়ী", "by year")}`}>
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

// Which chart explains a finding: water findings -> water chart, tree findings -> tree chart.
const metricFor = (f: RuleResultOut) => METRICS.find((m) => f.rule_id.includes(m.key.startsWith("water") ? "water" : "tree"));

function SatelliteResults({ check }: { check: SatelliteCheckOut }) {
  const en = useLang() === "en";
  const t = (b: string, e: string) => (en ? e : b);
  const r = check.result!;
  const findings = check.findings ?? [];
  const [detail, setDetail] = useState<RuleResultOut | null>(null);
  const detailMetric = detail ? metricFor(detail) : undefined;
  const detailTrend = detailMetric ? r.trends[detailMetric.key] : undefined;
  return (
    <div className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-2">
        {METRICS.map((m) => {
          const trend = r.trends[m.key];
          return trend ? <MetricChart key={m.key} label={en ? m.labelEn : m.label} unit={m.unit} trend={trend} outliers={trend.outlier_years} /> : null;
        })}
      </div>
      <p className="text-xs text-muted">{t("ভরাট বিন্দু: প্রবণতায় ধরা বছর। ফাঁপা বিন্দু: ব্যতিক্রমী বা কম নির্ভরযোগ্য বছর (বিন্দুর ওপর মাউস রাখলে কারণ দেখাবে)।", "Filled dots: years counted in the trend. Hollow dots: outlier or low-confidence years. Hover a dot to see why.")}</p>
      <section className="space-y-3">
        <h3 className="font-heading text-lg font-bold text-ink">{t("যা দেখা গেছে", "What was seen")}</h3>
        {findings.length ? findings.map((f) => (
          <FindingCard key={f.rule_id} tone={findingTone(f.status)} title={f.title_bn}
            footer={<button type="button" aria-haspopup="dialog" onClick={() => setDetail(f)} className="inline-flex min-h-11 items-center gap-2 rounded-[var(--radius-control)] border border-sat/30 bg-surface px-3 text-sm font-semibold text-sat shadow-rest hover:shadow-raised">{t("বিস্তারিত ও চার্ট", "Details and chart")} <span aria-hidden="true">→</span></button>}>
            <p className="text-sm leading-relaxed">{f.message_bn}</p>
            {typeof f.values?.next_action_bn === "string" && <p className="text-sm leading-relaxed"><strong>{t("এরপর:", "Next:")}</strong> {f.values.next_action_bn}</p>}
          </FindingCard>
        )) : <p className="rounded-xl border border-line bg-bg/40 p-3 text-sm text-muted">{t("স্যাটেলাইট ছবিতে আশেপাশে সতর্ক হওয়ার মতো কোনো পরিবর্তন ধরা পড়েনি। এর মানে এই নয় যে জমিতে কোনো সমস্যা নেই; মাঠে গিয়ে নিজে দেখুন।", "The satellite images show no nearby change that calls for caution. That does not mean the land has no problem; go and see it yourself.")}</p>}
      </section>
      <Modal
        open={!!detail}
        onClose={() => setDetail(null)}
        title={detail?.title_bn ?? ""}
        description={t("স্যাটেলাইট ছবি থেকে পাওয়া ফল; প্লটের চারপাশের প্রায় ২০০ মিটার এলাকার।", "Results from satellite images, for about 200 m around the plot.")}
      >
        {detail && (
          <div className="space-y-4">
            <TonePill tone={findingTone(detail.status)} />
            {detailMetric && detailTrend && <MetricChart label={en ? detailMetric.labelEn : detailMetric.label} unit={detailMetric.unit} trend={detailTrend} outliers={detailTrend.outlier_years} />}
            <p className="text-sm leading-7 text-ink">{detail.message_bn}</p>
            {typeof detail.values?.next_action_bn === "string" && (
              <div className="rounded-[var(--radius-control)] border border-accent/20 bg-accent-soft/60 p-3 text-sm leading-7"><strong>{t("এরপর:", "Next:")}</strong> {detail.values.next_action_bn}</div>
            )}
            <p className="text-xs leading-6 text-muted">{t("ভরাট বিন্দু: প্রবণতায় ধরা বছর। ফাঁপা বিন্দু: ব্যতিক্রমী বা কম নির্ভরযোগ্য বছর। স্যাটেলাইট যাচাই কাগজের পরীক্ষার ঝুঁকির মাত্রা বদলায় না; মাঠে গিয়ে নিজে মিলিয়ে দেখুন।", "Filled dots: years counted in the trend. Hollow dots: outlier or low-confidence years. The satellite check does not change the risk level from the papers; compare on the ground yourself.")}</p>
          </div>
        )}
      </Modal>
    </div>
  );
}

export function SatellitePanel({ landId, geometry }: { landId: string; geometry: PlotGeometry | null }) {
  const en = useLang() === "en";
  const t = (b: string, e: string) => (en ? e : b);
  const [shape, setShape] = useState(geometry);
  const [check, setCheck] = useState<SatelliteCheckOut | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0); // bump to fetch the latest check again
  const [loaded, setLoaded] = useState(false);
  const toast = useToast();

  useEffect(() => {
    let cancelled = false;
    let timer: number | undefined;
    api.getLatestSatelliteCheck(landId).then((latest) => {
      if (cancelled) return;
      setCheck(latest);
      if (latest.status === "pending") timer = window.setTimeout(() => setTick((t) => t + 1), POLL_MS);
    }).catch((e) => {
      if (!cancelled && !(e instanceof ApiError && e.status === 404)) setError(e instanceof Error ? e.message : LOAD_ERROR);
    }).finally(() => { if (!cancelled) setLoaded(true); });
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [landId, tick]);

  const start = async () => {
    setStarting(true);
    setError(null);
    try {
      setCheck(await api.startSatelliteCheck(landId));
      setTick((t) => t + 1);
      toast("info", t("স্যাটেলাইট যাচাই শুরু হয়েছে। ফল এলে এখানেই দেখাবে।", "Satellite check started. The result will show here."));
    } catch (e) {
      const msg = e instanceof Error ? e.message : t("যাচাই শুরু করা যায়নি।", "Could not start the check.");
      setError(msg);
      toast("bad", msg);
    } finally {
      setStarting(false);
    }
  };

  const pending = check?.status === "pending";
  return (
    <section className="surface-grad relative space-y-4 overflow-hidden rounded-[var(--radius-card)] border border-sat/30 bg-surface p-4 shadow-raised before:absolute before:inset-x-0 before:top-0 before:h-1 before:bg-gradient-to-r before:from-sat before:to-accent sm:p-5" aria-labelledby="satellite-title">
      <div className="space-y-2">
        <p className="inline-flex items-center gap-2 rounded-full bg-sat-soft px-3 py-1 text-xs font-semibold text-sat">
          <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" className="h-4 w-4"><path d="M4 12a8 8 0 0 1 8-8m-5 8a5 5 0 0 1 5-5m-1 8 7-7m-4 0h4v4M10 18l-2 2m6-6 6 6-2 2-6-6" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></svg>
          {t("মাঠের ছবি", "Field imagery")}
        </p>
        <h2 id="satellite-title" className="scroll-mt-40 font-heading text-xl font-bold text-ink">{t("স্যাটেলাইট যাচাই", "Satellite check")}</h2>
        <p className="text-sm leading-relaxed text-muted">{t("মানচিত্রে প্লটের সীমানা আঁকুন। ২০১৯ থেকে প্রতি বছরের ফেব্রুয়ারির (শুকনো মৌসুম) স্যাটেলাইট ছবিতে প্লটের আশেপাশে গাছ ও পানি কেমন বদলেছে তা দেখা হবে।", "Draw the plot boundary on the map. February (dry season) satellite images from 2019 onward show how trees and water around the plot changed.")}</p>
        <p className="flex items-start gap-2 text-xs leading-relaxed text-muted">
          <span aria-hidden="true" className="mt-0.5 inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-muted text-[10px] font-bold">i</span>
          {t("ছবির প্রতিটি বিন্দু ১০ মিটার, তাই ফলাফল প্লটের চারপাশের প্রায় ২০০ মিটার এলাকার, প্লটের সীমানার ভেতরের নয়।", "Each image pixel is 10 m, so results cover about 200 m around the plot, not only inside its boundary.")}
        </p>
      </div>
      <div className="-mx-4 sm:mx-0">
        <PlotMap landId={landId} geometry={geometry} onSaved={(g) => { setShape(g); toast("ok", t("সীমানা রাখা হয়েছে।", "Boundary saved.")); }} />
      </div>
      {!shape && (
        <div className="rounded-[var(--radius-card)] border border-dashed border-line bg-bg/60 p-4 text-sm leading-relaxed">
          <p className="font-semibold text-ink">{t("এখনো সীমানা আঁকা হয়নি", "No boundary drawn yet")}</p>
          <ol className="mt-1 list-decimal space-y-0.5 pl-5 text-muted">
            <li>{t("মানচিত্রের ডান দিকের বহুভুজ বোতাম চাপুন।", "Press the polygon button on the right of the map.")}</li>
            <li>{t("প্লটের প্রতিটি কোণে একবার করে ক্লিক করুন, শেষে প্রথম বিন্দুতে ক্লিক করুন।", "Click once on each corner of the plot, then click the first point to finish.")}</li>
            <li>{t("“সীমানা রাখুন” চাপুন, তারপর স্যাটেলাইট যাচাই শুরু করুন।", "Press “Save boundary”, then start the satellite check.")}</li>
          </ol>
        </div>
      )}
      <div className="flex flex-wrap items-center gap-3">
        <button type="button" onClick={start} disabled={!shape || starting || pending} className="min-h-11 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white">
          {starting ? t("শুরু হচ্ছে…", "Starting…") : pending ? t("যাচাই চলছে…", "Checking…") : t("স্যাটেলাইট যাচাই করুন", "Run satellite check")}
        </button>
        {check && !pending && <span className="text-xs text-muted">{t("শেষ যাচাই:", "Last check:")} {new Date(check.created_at).toLocaleString(en ? "en-GB" : "bn-BD")}</span>}
      </div>
      {(pending || starting) && (
        <div role="status" aria-live="polite" className="flex items-start gap-3 rounded-[var(--radius-card)] border border-sat/30 bg-sat-soft p-4 text-sm">
          <Spinner size="sm" />
          <div className="space-y-1">
            <p className="font-semibold text-ink">{t("স্যাটেলাইট ছবি দেখা হচ্ছে…", "Looking at satellite images…")}</p>
            <p className="leading-relaxed text-muted">{t("২০১৯ থেকে ২০২৫ পর্যন্ত সাত বছরের ছবি দেখতে সাধারণত এক থেকে কয়েক মিনিট লাগে। এই পাতা খোলা রাখুন, ফল এলে এখানেই দেখাবে।", "Seven years of images (2019 to 2025) usually take one to a few minutes. Keep this page open; the result will show here.")}</p>
          </div>
        </div>
      )}
      {error && <p role="alert" className="rounded-lg border border-bad/40 bg-bad-bg p-3 text-sm">{error === LOAD_ERROR ? t("ফল আনা যায়নি।", "Could not load the result.") : error}</p>}
      {check?.status === "failed" && <p role="alert" className="rounded-lg border border-bad/40 bg-bad-bg p-3 text-sm">{check.error || t("যাচাই করা যায়নি।", "The check failed.")}</p>}
      {!loaded && (
        <div role="status" aria-label={t("স্যাটেলাইট ফল লোড হচ্ছে", "Loading satellite result")} className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2"><Skeleton className="h-48 w-full !rounded-[var(--radius-card)]" /><Skeleton className="h-48 w-full !rounded-[var(--radius-card)]" /></div>
          <Skeleton className="h-20 w-full !rounded-[var(--radius-card)]" />
        </div>
      )}
      {check?.status === "ok" && check.result && <SatelliteResults check={check} />}
      {check?.status === "ok" && <p className="rounded-lg bg-bg p-3 text-xs leading-relaxed text-muted">{!en && check.area_note_bn} {t("স্যাটেলাইট যাচাই কাগজের পরীক্ষার ঝুঁকির মাত্রা বদলায় না।", "The satellite check does not change the risk level from the papers.")}</p>}
    </section>
  );
}
