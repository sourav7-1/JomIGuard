"use client";

import React, { useEffect, useState } from "react";
import { api, LandCaseViewOut, SatelliteCheckOut } from "@/lib/api";

type Tone = "done" | "warn" | "bad" | "running" | "todo";
type Step = { label: string; status: string; tone: Tone; href: string };

const BN = "০১২৩৪৫৬৭৮৯";
const bn = (n: number) => String(n).replace(/\d/g, (d) => BN[Number(d)]);

const toneStyle: Record<Tone, { dot: string; text: string; mark: string }> = {
  done: { dot: "border-ok bg-ok text-white", text: "text-ok", mark: "✓" },
  warn: { dot: "border-warn bg-warn-bg text-warn", text: "text-warn", mark: "!" },
  bad: { dot: "border-bad bg-bad-bg text-bad", text: "text-bad", mark: "!" },
  running: { dot: "border-sat bg-sat-soft text-sat", text: "text-sat", mark: "…" },
  todo: { dot: "border-line bg-surface text-muted", text: "text-muted", mark: "" },
};

type NextAction = { text: string; rank: number };

// Only text the app already produced: open rule actions (priority 1 = most urgent) and the
// satellite findings' next_action_bn (bad/warn before skipped). Most severe first, at most 3.
export function nextActions(caseView: LandCaseViewOut, check: SatelliteCheckOut | null): string[] {
  const out: NextAction[] = (caseView.latest_assessment?.actions ?? [])
    .filter((a) => !a.done)
    .map((a) => ({ text: a.text_bn, rank: a.priority }));
  for (const f of check?.status === "ok" ? check.findings ?? [] : []) {
    const text = f.values?.next_action_bn;
    if (typeof text === "string") out.push({ text, rank: f.status === "bad" ? 1 : f.status === "warn" ? 2 : 3 });
  }
  const seen = new Set<string>();
  return out
    .map((a, i) => ({ ...a, i }))
    .sort((a, b) => a.rank - b.rank || a.i - b.i)
    .filter((a) => !seen.has(a.text) && seen.add(a.text))
    .slice(0, 3)
    .map((a) => a.text);
}

function steps(caseView: LandCaseViewOut, check: SatelliteCheckOut | null, checkLoaded: boolean): Step[] {
  const docs = caseView.documents;
  const a = caseView.latest_assessment;
  const processing = docs.filter((d) => d.status === "uploaded" || d.status === "processing").length;
  const failed = docs.filter((d) => d.status === "failed" || d.latest_extraction?.status === "failed").length;
  const review = (a?.review_needed?.length ?? 0) + docs.filter((d) => d.latest_extraction?.status === "needs_review").length;
  const risk = a?.risk_level;

  const read: Pick<Step, "status" | "tone"> = !docs.length ? { status: "কাগজ নেই", tone: "todo" }
    : processing ? { status: "পড়া চলছে", tone: "running" }
    : failed ? { status: `${bn(failed)}টি পড়া যায়নি`, tone: "bad" }
    : review ? { status: "কিছু ঘর দেখে নিন", tone: "warn" }
    : { status: "সব পড়া হয়েছে", tone: "done" };
  const compare: Pick<Step, "status" | "tone"> = !a ? { status: "এখনো হয়নি", tone: "todo" }
    : caseView.assessment_stale ? { status: "তথ্য বদলেছে, আবার মিলান", tone: "warn" }
    : risk === "high" ? { status: "উচ্চ ঝুঁকি", tone: "bad" }
    : risk === "medium" ? { status: "মাঝারি ঝুঁকি", tone: "warn" }
    : { status: "কম ঝুঁকি", tone: "done" };
  const sat: Pick<Step, "status" | "tone"> = !checkLoaded ? { status: "দেখা হচ্ছে…", tone: "todo" }
    : !check ? { status: "শুরু হয়নি", tone: "todo" }
    : check.status === "pending" ? { status: "চলছে", tone: "running" }
    : check.status === "failed" ? { status: "করা যায়নি", tone: "bad" }
    : (check.findings ?? []).some((f) => f.status === "warn" || f.status === "bad") ? { status: `${bn((check.findings ?? []).length)}টি বিষয় দেখুন`, tone: "warn" }
    : { status: "শেষ হয়েছে", tone: "done" };

  return [
    { label: "কাগজ জমা", href: "#source-document-panel", ...(docs.length ? { status: `${bn(docs.length)}টি নথি`, tone: "done" as Tone } : { status: "কাগজ যোগ করুন", tone: "todo" as Tone }) },
    { label: "তথ্য পড়া", href: "#source-document-panel", ...read },
    { label: "মিলিয়ে দেখা", href: "#risk-summary", ...compare },
    { label: "স্যাটেলাইট যাচাই", href: "#satellite-title", ...sat },
    { label: "রিপোর্ট", href: "#risk-summary", ...(a ? { status: "PDF নেওয়া যায়", tone: "done" as Tone } : { status: "মিলানোর পরে", tone: "todo" as Tone }) },
  ];
}

export function CaseTracker({ landId, caseView }: { landId: string; caseView: LandCaseViewOut }) {
  const [check, setCheck] = useState<SatelliteCheckOut | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api.getLatestSatelliteCheck(landId)
      .then((c) => { if (!cancelled) setCheck(c); })
      .catch(() => { /* 404 = no check yet */ })
      .finally(() => { if (!cancelled) setLoaded(true); });
    return () => { cancelled = true; };
  }, [landId]);

  const list = steps(caseView, check, loaded);
  const todo = nextActions(caseView, check);

  return (
    <section aria-labelledby="tracker-title" className="space-y-4 rounded-[var(--radius-card)] border border-line bg-surface p-4 shadow-[var(--shadow-card)] sm:p-5">
      <h2 id="tracker-title" className="font-heading text-xl font-bold text-ink">যাচাইয়ের অবস্থা</h2>
      <ol className="grid gap-2 md:grid-cols-5 md:gap-0">
        {list.map((s, i) => {
          const t = toneStyle[s.tone];
          return (
            <li key={s.label} className="relative md:px-1">
              {i > 0 && <span aria-hidden="true" className={`absolute left-[-50%] right-[50%] top-5 hidden h-0.5 md:block ${list[i - 1].tone === "todo" ? "bg-line" : "bg-ok/50"}`} />}
              <a href={s.href} className="relative flex min-h-12 items-center gap-3 rounded-lg p-1.5 hover:bg-bg md:flex-col md:items-center md:gap-1.5 md:text-center">
                <span className={`relative z-10 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 text-sm font-bold ${t.dot}`}>
                  {t.mark || bn(i + 1)}
                </span>
                <span className="min-w-0">
                  <span className="block text-sm font-semibold leading-snug text-ink">{bn(i + 1)}. {s.label}</span>
                  <span className={`block text-xs font-medium leading-snug ${t.text}`}>{s.status}</span>
                </span>
              </a>
            </li>
          );
        })}
      </ol>
      <div className="rounded-[var(--radius-card)] border border-accent/25 bg-accent-soft/60 p-4">
        <h3 className="font-semibold text-ink">এখন কী করবেন</h3>
        {todo.length ? (
          <ol className="mt-2 list-decimal space-y-1.5 pl-5 text-sm leading-7 text-ink">
            {todo.map((t) => <li key={t}>{t}</li>)}
          </ol>
        ) : (
          <p className="mt-1 text-sm leading-6 text-muted">এখনো কোনো খোলা কাজ নেই। কাগজ যোগ করে মিলিয়ে দেখলে এখানে পরের কাজ দেখাবে।</p>
        )}
        <a href="#actions-title" className="mt-2 inline-flex min-h-11 items-center text-sm font-semibold text-accent underline underline-offset-4">সব কাজের তালিকা দেখুন</a>
      </div>
    </section>
  );
}
