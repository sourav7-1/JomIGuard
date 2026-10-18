"use client";

import React, { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { api, TimelineEvent, TimelineOut } from "@/lib/api";
import { strings } from "@/lib/strings";

const statusClass = { ok: "bg-ok", warn: "bg-warn", bad: "bg-bad" };

function TimelineContent() {
  const { id } = useParams<{ id: string }>();
  const [timeline, setTimeline] = useState<TimelineOut | null>(null);
  const [error, setError] = useState(false);
  const [open, setOpen] = useState<string | null>(null);
  useEffect(() => {
    api.getTimeline(id).then(setTimeline).catch(() => setError(true));
  }, [id]);
  if (error) return <p role="alert" className="mx-auto max-w-3xl p-6 text-sm text-bad">{strings.pages.caseTimeline.error}</p>;
  if (!timeline) return <div className="flex justify-center p-12"><Spinner size="lg" /></div>;
  const proposedSellers = new Set(timeline.events.filter((event) => event.kind === "proposed_sale").flatMap((event) => event.from_owners.map((owner) => owner.name)));
  return <main className="mx-auto max-w-3xl space-y-6 px-4 py-6">
    <header className="space-y-3">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">JomiGuard · Case history</p>
      <h1 className="font-heading text-2xl font-bold text-ink">{timeline.title_bn}</h1>
      <p className="text-sm leading-6 text-muted">{strings.pages.caseTimeline.desc}</p>
      <Link href={`/cases/${id}`} className="inline-flex min-h-11 items-center rounded-lg border border-line bg-surface px-4 text-sm font-semibold text-ink">{strings.pages.caseTimeline.backToCase}</Link>
    </header>
    <div aria-label="Timeline legend" className="flex flex-wrap gap-x-4 gap-y-2 rounded-xl border border-line bg-surface p-3 text-xs">
      {(Object.keys(strings.pages.caseTimeline.legend) as Array<keyof typeof strings.pages.caseTimeline.legend>).map((status) => <span key={status} className="inline-flex items-center gap-2"><i className={`h-2.5 w-2.5 rounded-full ${statusClass[status]}`} />{strings.pages.caseTimeline.legend[status]}</span>)}
    </div>
    {!timeline.events.length ? <Card className="p-6 text-sm text-muted">{strings.pages.caseTimeline.empty}</Card> : <ol className="relative space-y-4 border-l-2 border-line pl-5 sm:pl-7">
      {timeline.events.map((event: TimelineEvent, index) => {
        const key = `${event.kind}-${index}`;
        const expanded = open === key;
        const parties = event.kind === "inheritance" ? event.to_owners : [...event.from_owners, ...event.to_owners];
        return <li key={key} className="relative">
          <span className={`absolute -left-[1.68rem] top-5 h-3.5 w-3.5 rounded-full ring-4 ring-bg sm:-left-[2.18rem] ${statusClass[event.status]}`} />
          <button type="button" aria-expanded={expanded} onClick={() => setOpen(expanded ? null : key)} className="w-full rounded-xl border border-line bg-surface p-4 text-left shadow-sm hover:border-accent/40 focus-visible:outline-2 focus-visible:outline-accent">
            <div className="flex flex-wrap items-center justify-between gap-2"><span className="text-xs font-semibold text-accent">{strings.pages.caseTimeline.kinds[event.kind as keyof typeof strings.pages.caseTimeline.kinds] || event.kind}</span><span className="text-xs text-muted">{event.year ?? "—"}</span></div>
            <h2 className="mt-2 font-heading text-lg font-bold text-ink">{event.title_bn}</h2>
            <p className="mt-1 text-sm leading-6 text-muted">{event.detail_bn}</p>
            {event.area && <p className="mt-2 text-xs text-muted">{strings.pages.caseTimeline.area}: {event.area}</p>}
            {parties.length > 0 && <div className="mt-3 grid gap-3 sm:grid-cols-2">
              {(event.kind === "inheritance" ? [[strings.pages.caseTimeline.heirs, parties]] : [[strings.pages.caseTimeline.from, event.from_owners], [strings.pages.caseTimeline.to, event.to_owners]]).map(([label, list]) => <div key={String(label)} className="rounded-lg bg-bg p-3"><p className="mb-2 text-xs font-semibold text-muted">{label as string}</p><ul className="space-y-1.5">{(list as typeof parties).map((party, i) => <li key={`${party.name}-${i}`} className={`break-words text-sm ${proposedSellers.has(party.name) ? "rounded-md border border-accent/40 bg-surface px-2 py-1 font-semibold text-accent" : "text-ink"}`}>{party.name}{party.share_text && <span className="ml-1 text-xs text-muted">· {strings.pages.caseTimeline.share} {party.share_text}</span>}{proposedSellers.has(party.name) && <span className="ml-1 text-xs">({strings.pages.caseTimeline.seller})</span>}</li>)}</ul></div>)}
            </div>}
            {event.finding_codes.length > 0 && <p className="mt-3 text-xs font-medium text-bad">{event.finding_codes.join(" · ")}</p>}
            {expanded && <div className="mt-4 border-t border-line pt-3"><p className="mb-2 text-xs font-semibold text-muted">{strings.pages.caseTimeline.source}</p><div className="flex flex-col gap-2">{event.sources.map((source, i) => <Link key={`${source.source_id}-${source.field_path}-${i}`} href={`/cases/${id}?source=${encodeURIComponent(source.source_id)}&field=${encodeURIComponent(source.field_path)}`} className="min-h-11 break-words rounded-lg border border-line bg-bg px-3 py-2 text-sm text-accent underline">{source.label_bn} · {source.value_bn || source.printed_text || source.field_path}</Link>)}</div></div>}
          </button>
        </li>;
      })}
    </ol>}
  </main>;
}

export default function CaseTimelinePage() {
  return <Suspense fallback={<div className="flex justify-center p-12"><Spinner size="lg" /></div>}><TimelineContent /></Suspense>;
}
