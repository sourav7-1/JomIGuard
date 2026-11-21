"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, LandOut } from "@/lib/api";
import { strings } from "@/lib/strings";
import { Card } from "@/components/ui/Card";
import { ListSkeleton } from "@/components/ui/Skeleton";
import { isListedLand } from "@/lib/bd-locations";
import { bnDigits } from "@/lib/digits";

const bn = bnDigits;

export default function CasesPage() {
  const [lands, setLands] = useState<LandOut[] | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => { api.getLands().then((rows) => setLands(rows.filter(isListedLand))).catch(() => setError(true)); }, []);
  return <div className="mx-auto max-w-5xl space-y-8 py-2 sm:space-y-10">
    <div className="flex flex-col gap-5 border-b border-line pb-7 sm:flex-row sm:items-end sm:justify-between">
      <div className="max-w-2xl"><p className="mb-3 flex items-center gap-3 text-sm font-semibold text-accent"><span className="h-px w-8 bg-gold" />আপনার নথির কাজ</p><h1 className="text-3xl font-semibold leading-tight tracking-tight text-ink sm:text-4xl">{strings.pages.cases.title}</h1><p className="mt-3 text-base leading-7 text-muted">{strings.pages.cases.desc}</p></div>
      <Link href="/find" className="inline-flex min-h-11 shrink-0 items-center justify-center rounded-[var(--radius-control)] bg-accent px-4 text-sm font-semibold text-white shadow-rest">নতুন যাচাই শুরু করুন</Link>
    </div>
    {error ? <p role="alert" className="border-y border-line py-10 text-sm text-bad">{strings.pages.cases.error}</p> : lands === null ? <ListSkeleton /> : lands.length === 0 ? <div className="border-y border-line py-10"><p className="text-sm leading-6 text-muted">{strings.pages.cases.empty}</p><Link href="/find" className="mt-4 inline-flex min-h-11 items-center rounded-md border border-line bg-surface px-4 text-sm font-semibold text-accent">নতুন যাচাই শুরু করুন</Link></div> : <ul className="grid gap-3 sm:grid-cols-2">{lands.map((land, i) => <Card key={land.id} as="li" variant="interactive" href={`/cases/${land.id}`} className="animate-fade-up" style={{ ["--i" as string]: Math.min(i, 8) }}
      title={<>{land.mouza || "মৌজার তথ্য নেই"} · দাগ {bn(land.dag_no || "—")}</>}
      description={<>{[land.upazila, land.district].filter(Boolean).join(", ")} · খতিয়ান {bn(land.khatian_no || "—")}</>}
      footer={<span aria-hidden="true" className="inline-flex min-h-11 items-center gap-1 text-sm font-semibold text-accent">{strings.pages.cases.open} →</span>} />)}</ul>}
  </div>;
}
