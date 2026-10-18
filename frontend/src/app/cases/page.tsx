"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, LandOut } from "@/lib/api";
import { strings } from "@/lib/strings";
import { Spinner } from "@/components/ui/Spinner";

export default function CasesPage() {
  const [lands, setLands] = useState<LandOut[] | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => { api.getLands().then(setLands).catch(() => setError(true)); }, []);
  return <div className="mx-auto max-w-5xl space-y-8 py-2 sm:space-y-10">
    <div className="flex flex-col gap-5 border-b border-line pb-7 sm:flex-row sm:items-end sm:justify-between">
      <div className="max-w-2xl"><p className="mb-3 flex items-center gap-3 text-sm font-semibold text-accent"><span className="h-px w-8 bg-gold" />আপনার নথির কাজ</p><h1 className="text-3xl font-semibold leading-tight tracking-tight text-ink sm:text-4xl">{strings.pages.cases.title}</h1><p className="mt-3 text-base leading-7 text-muted">{strings.pages.cases.desc}</p></div>
      <Link href="/upload" className="inline-flex min-h-11 shrink-0 items-center justify-center rounded-md bg-accent px-4 text-sm font-semibold text-white">নতুন যাচাই শুরু করুন</Link>
    </div>
    {error ? <p role="alert" className="border-y border-line py-10 text-sm text-bad">{strings.pages.cases.error}</p> : lands === null ? <div className="flex justify-center py-10"><Spinner /></div> : lands.length === 0 ? <div className="border-y border-line py-10"><p className="text-sm leading-6 text-muted">{strings.pages.cases.empty}</p><Link href="/upload" className="mt-4 inline-flex min-h-11 items-center rounded-md border border-line bg-surface px-4 text-sm font-semibold text-accent">নতুন যাচাই শুরু করুন</Link></div> : <ul className="grid gap-3 sm:grid-cols-2">{lands.map((land) => <li key={land.id} className="rounded-xl border border-line bg-surface p-4"><p className="font-heading text-lg font-bold text-ink">{land.mouza || "মৌজার তথ্য নেই"} · দাগ {land.dag_no || "—"}</p><p className="mt-1 text-sm text-muted">{land.district} {land.upazila} · খতিয়ান {land.khatian_no || "—"}</p><Link href={`/cases/${land.id}`} className="mt-3 inline-flex min-h-11 items-center text-sm font-semibold text-accent underline">{strings.pages.cases.open}</Link></li>)}</ul>}
  </div>;
}
