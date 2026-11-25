"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, LandListItemOut } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { ListSkeleton } from "@/components/ui/Skeleton";
import { RiskBadge } from "@/components/ui/VerdictBox";
import { bnDigits } from "@/lib/digits";
import { groupByPlot, riskBadge } from "@/lib/journey";
import { useLang } from "@/lib/lang";

export default function DashboardPage() {
  const en = useLang() === "en";
  const t = (b: string, e: string) => (en ? e : b);
  const num = (v: string | number) => (en ? String(v) : bnDigits(v));
  const [groups, setGroups] = useState<LandListItemOut[][] | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    api.getLands().then((rows) => setGroups(groupByPlot(rows.filter((l) => l.summary.listed)))).catch(() => setError(true));
  }, []);

  const card = (land: LandListItemOut) => {
    const s = land.summary;
    const updated = new Date(s.updated_at).toLocaleDateString(en ? "en-GB" : "bn-BD", { day: "numeric", month: "short", year: "numeric" });
    return (
      <Card key={land.id} as="div" variant="interactive" href={`/cases/${land.id}`}
        title={<>{land.mouza} · {t("দাগ", "dag")} {num(land.dag_no)}</>}
        description={
          <span className="block space-y-2">
            <span className="block">{[land.upazila, land.district].filter(Boolean).join(", ")}</span>
            <span className="flex flex-wrap items-center gap-2">
              <RiskBadge riskLevel={riskBadge(s.risk_level, s.complete)} />
              <span className="text-sm font-semibold text-ink">{t("অগ্রগতি", "Progress")} {num(s.progress_done)}/{num(s.progress_total)}</span>
            </span>
            {s.next_action_bn && <span className="block text-sm text-ink">{t("এখন কী করবেন", "Next")}: {s.next_action_bn}</span>}
            <span className="block text-xs text-muted">{t("শেষ হালনাগাদ", "Last updated")}: {updated}</span>
          </span>
        } />
    );
  };

  return (
    <div className="space-y-8">
      <section className="flex flex-col gap-5 border-b border-line pb-7 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-ink sm:text-4xl">{t("আমার কেস", "My cases")}{groups && <span className="ml-2 text-base font-normal text-muted">({num(groups.length)})</span>}</h1>
          <p className="mt-3 text-base leading-7 text-muted">{t("প্রতিটি জমির যাচাই কোথায় আছে আর এরপর কী করতে হবে।", "Where each plot's check stands and what to do next.")}</p>
        </div>
        <Link href="/find" className="inline-flex min-h-11 shrink-0 items-center justify-center rounded-[var(--radius-control)] bg-accent px-4 text-sm font-semibold text-white shadow-rest">{t("নতুন যাচাই শুরু করুন", "Start a new check")}</Link>
      </section>

      {error ? <p role="alert" className="text-sm text-bad">{t("কেস তালিকা আনা যায়নি।", "Could not load your cases.")}</p>
        : groups === null ? <ListSkeleton />
        : groups.length === 0 ? (
          <div className="rounded-xl border border-dashed border-line bg-surface/50 p-8 text-center">
            <p className="font-semibold text-ink">{t("এখনো কোনো কেস নেই", "No cases yet")}</p>
            <p className="mt-2 text-sm text-muted">{t("মৌজা আর দাগ দিয়ে প্রথম জমির যাচাই শুরু করুন, অথবা ", "Start your first check with a mouza and dag, or ")}<Link href="/demo" className="font-semibold text-accent underline underline-offset-4">{t("নমুনা ডেটা দেখুন", "try the demo data")}</Link>.</p>
          </div>
        )
        : <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{groups.map(([latest, ...older]) => (
          <li key={latest.id} className="space-y-2">
            {card(latest)}
            {older.length > 0 && (
              <details className="rounded-[var(--radius-control)] border border-line bg-surface px-3 py-2 text-sm">
                <summary className="min-h-11 cursor-pointer content-center font-semibold text-accent">{t(`আরো ${num(older.length)} টি`, `${older.length} more`)}</summary>
                <div className="mt-2 space-y-2">{older.map(card)}</div>
              </details>
            )}
          </li>
        ))}</ul>}
    </div>
  );
}
