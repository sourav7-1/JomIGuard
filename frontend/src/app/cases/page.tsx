"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, LandOut } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { ListSkeleton } from "@/components/ui/Skeleton";
import { isListedLand } from "@/lib/bd-locations";
import { bnDigits } from "@/lib/digits";
import { useLang, useStrings } from "@/lib/lang";

export default function CasesPage() {
  const en = useLang() === "en";
  const s = useStrings();
  const t = (b: string, e: string) => (en ? e : b);
  const num = (v: string) => (en ? v : bnDigits(v));
  const [lands, setLands] = useState<LandOut[] | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => { api.getLands().then((rows) => setLands(rows.filter(isListedLand))).catch(() => setError(true)); }, []);
  const newCheck = t("নতুন যাচাই শুরু করুন", "Start a new check");
  return <div className="mx-auto max-w-5xl space-y-8 py-2 sm:space-y-10">
    <div className="flex flex-col gap-5 border-b border-line pb-7 sm:flex-row sm:items-end sm:justify-between">
      <div className="max-w-2xl"><p className="mb-3 flex items-center gap-3 text-sm font-semibold text-accent"><span className="h-px w-8 bg-gold" />{t("আপনার নথির কাজ", "Your document work")}</p><h1 className="text-3xl font-semibold leading-tight tracking-tight text-ink sm:text-4xl">{s.pages.cases.title}</h1><p className="mt-3 text-base leading-7 text-muted">{s.pages.cases.desc}</p></div>
      <Link href="/find" className="inline-flex min-h-11 shrink-0 items-center justify-center rounded-[var(--radius-control)] bg-accent px-4 text-sm font-semibold text-white shadow-rest">{newCheck}</Link>
    </div>
    {error ? <p role="alert" className="border-y border-line py-10 text-sm text-bad">{s.pages.cases.error}</p> : lands === null ? <ListSkeleton /> : lands.length === 0 ? <div className="border-y border-line py-10"><p className="text-sm leading-6 text-muted">{s.pages.cases.empty}</p><Link href="/find" className="mt-4 inline-flex min-h-11 items-center rounded-md border border-line bg-surface px-4 text-sm font-semibold text-accent">{newCheck}</Link></div> : <ul className="grid gap-3 sm:grid-cols-2">{lands.map((land, i) => <Card key={land.id} as="li" variant="interactive" href={`/cases/${land.id}`} className="animate-fade-up" style={{ ["--i" as string]: Math.min(i, 8) }}
      title={<>{land.mouza || t("মৌজার তথ্য নেই", "No mouza")} · {t("দাগ", "Dag")} {num(land.dag_no || "—")}</>}
      description={<>{[land.upazila, land.district].filter(Boolean).join(", ")} · {t("খতিয়ান", "Khatian")} {num(land.khatian_no || "—")}</>}
      footer={<span aria-hidden="true" className="inline-flex min-h-11 items-center gap-1 text-sm font-semibold text-accent">{s.pages.cases.open} →</span>} />)}</ul>}
  </div>;
}
