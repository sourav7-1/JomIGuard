"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { demoPacks, demoPlots, preparedCases, type DemoPack } from "@/lib/demo-packs";
import { Card } from "@/components/ui/Card";
import { En } from "@/components/ui/En";
import { Modal } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";
import { startTour } from "@/components/GuidedTour";
import { bnDigits } from "@/lib/digits";

const btn = "inline-flex min-h-11 flex-col justify-center rounded-[var(--radius-control)] px-3 py-1 text-sm font-semibold";
const primary = `${btn} bg-accent text-white shadow-rest hover:shadow-raised disabled:opacity-60`;
const ghost = `${btn} border border-line bg-surface text-ink hover:bg-bg`;
const bnNum = bnDigits;
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function H2({ id, bn, en, line }: { id: string; bn: string; en: string; line?: string }) {
  return (
    <div>
      <h2 id={id} className="font-heading text-2xl font-bold text-ink">{bn}<En className="mt-0.5 text-sm text-muted">{en}</En></h2>
      {line && <p className="mt-1 text-sm leading-6 text-muted">{line}</p>}
    </div>
  );
}

export default function DemoPage() {
  const router = useRouter();
  const toast = useToast();
  const [expected, setExpected] = useState<DemoPack | null>(null);
  const [progress, setProgress] = useState<{ title: string; text: string } | null>(null);

  // One click: new case from the pack -> wait for every page to be read -> check -> open at the findings.
  const packCase = async (pack: DemoPack) => {
    setProgress({ title: pack.title, text: "নতুন কেস তৈরি হচ্ছে…" });
    try {
      const land = await api.demoPackCase(pack.id);
      for (let t = 0; t < 120; t++) {
        const docs = await api.getLandDocuments(land.id);
        const done = docs.filter((d) => d.status === "done" || d.status === "failed").length;
        setProgress({ title: pack.title, text: `নথি পড়া হচ্ছে: ${bnNum(done)} / ${bnNum(docs.length)}` });
        if (docs.length && done === docs.length) {
          if (docs.some((d) => d.status === "failed")) toast("bad", "কিছু নথি পড়া যায়নি; কেসে গিয়ে আবার চেষ্টা করুন।");
          break;
        }
        await sleep(3000);
      }
      setProgress({ title: pack.title, text: "কাগজগুলো মিলিয়ে দেখা হচ্ছে…" });
      await api.assessLand(land.id).catch(() => undefined);
      setProgress(null);
      toast("ok", "আপনার নতুন কেস তৈরি হয়েছে।");
      const path = `/cases/${land.id}`;
      router.push(path);
      startTour(3, path);
    } catch (e) {
      setProgress(null);
      toast("bad", e instanceof Error ? e.message : "কেস তৈরি করা যায়নি।");
    }
  };

  // Satellite: new case with the plot's outline, start a live check, open the satellite panel.
  const plotCase = async (plotId: string, title: string) => {
    setProgress({ title, text: "প্লটসহ নতুন কেস তৈরি হচ্ছে…" });
    try {
      const land = await api.demoPlotCase(plotId);
      try { await api.startSatelliteCheck(land.id); toast("info", "স্যাটেলাইট যাচাই শুরু হয়েছে; কয়েক মিনিট লাগতে পারে।"); }
      catch (e) { toast("bad", e instanceof Error ? e.message : "যাচাই শুরু করা যায়নি।"); }
      setProgress(null);
      const path = `/cases/${land.id}`;
      router.push(path);
      startTour(4, path);
    } catch (e) {
      setProgress(null);
      toast("bad", e instanceof Error ? e.message : "কেস তৈরি করা যায়নি।");
    }
  };

  const geojson = async (plotId: string) => {
    try {
      const res = await fetch("/api/demo/plots", { credentials: "include" });
      const plot = (await res.json() as { id: string; geometry: unknown }[]).find((p) => p.id === plotId);
      if (!plot) throw new Error();
      const url = URL.createObjectURL(new Blob([JSON.stringify({ type: "Feature", properties: { name: plotId, note: "synthetic demo plot" }, geometry: plot.geometry }, null, 2)], { type: "application/geo+json" }));
      const a = document.createElement("a"); a.href = url; a.download = `jomiguard-plot-${plotId}.geojson`; a.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch { toast("bad", "GeoJSON নামানো যায়নি।"); }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-10 pb-10">
      <header className="hero-glow space-y-3">
        <p className="text-sm font-semibold text-accent">বিচারকদের জন্য<En>For judges</En></p>
        <h1 className="font-heading text-4xl font-bold text-ink sm:text-5xl">নমুনা ডেটা<En className="mt-1 text-base text-muted">Demo data</En></h1>
        <p className="max-w-2xl text-base leading-7 text-muted">সব নথি কৃত্রিম, “নমুনা / SAMPLE” ছাপ দেওয়া; আসল কারো নাম বা নম্বর নেই। এক ক্লিকে আপনার নিজের নতুন কেস তৈরি হয়, প্রস্তুত নমুনা কেস বদলায় না।<En>All documents are synthetic and watermarked. One click makes your own new case; prepared samples never change.</En></p>
      </header>

      <section aria-labelledby="packs-title" className="space-y-4">
        <H2 id="packs-title" bn="নথির নমুনা প্যাক" en="Document packs" line="প্রতিটি প্যাকে খতিয়ান, দলিল ও নামজারি (ডি-তে ওয়ারিশ সনদও)।" />
        <ul className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {demoPacks.map((p, i) => (
            <Card key={p.id} as="li" className="animate-fade-up flex flex-col" style={{ "--i": i } as React.CSSProperties}
              icon={<span aria-hidden="true" className="inline-flex h-11 w-11 items-center justify-center rounded-[var(--radius-control)] bg-gradient-to-br from-accent-soft to-surface font-mono text-lg font-bold text-accent shadow-rest">{p.id}</span>}
              title={<>{p.title}<En className="text-muted">{p.en}</En></>} titleAs="h3"
              description={<>{p.shows}<En className="mt-0.5">{p.showsEn}</En></>}
              footer={<div className="flex flex-wrap gap-2">
                <button type="button" aria-haspopup="dialog" onClick={() => setExpected(p)} className={ghost}>প্রত্যাশিত ফল<En>Expected result</En></button>
                <a href={`/api/demo/packs/${p.id}.zip`} download className={ghost}>ফাইল ডাউনলোড<En>Download (ZIP)</En></a>
                <button type="button" onClick={() => void packCase(p)} disabled={!!progress} className={primary}>এক ক্লিকে কেস তৈরি<En>One-click case</En></button>
              </div>} />
          ))}
        </ul>
      </section>

      <section aria-labelledby="plots-title" className="space-y-4">
        <H2 id="plots-title" bn="স্যাটেলাইট নমুনা প্লট" en="Satellite demo plots" line="লাইভ যাচাই এক ঘণ্টায় সর্বোচ্চ ৫টি; একটিতে কয়েক মিনিট লাগে।" />
        <ul className="grid gap-4 md:grid-cols-2">
          {demoPlots.map((p) => (
            <Card key={p.id} as="li" variant="satellite" title={<>{p.title}<En className="text-muted">{p.en}</En></>} titleAs="h3" description={p.shows}
              footer={<div className="flex flex-wrap gap-2">
                {p.caseHref && <Link href={p.caseHref} className={ghost}>ম্যাপে দেখুন<En>View on map</En></Link>}
                <button type="button" onClick={() => void plotCase(p.id, p.title)} disabled={!!progress} className={`${btn} bg-sat text-white shadow-rest disabled:opacity-60`}>এই প্লট দিয়ে যাচাই করুন<En>Run a live check</En></button>
                <button type="button" onClick={() => void geojson(p.id)} className={ghost}>GeoJSON<En>Download outline</En></button>
              </div>}>
              <p className="rounded-[var(--radius-control)] bg-sat-soft/60 p-3 text-sm leading-6 text-ink"><b>রেকর্ড করা ফল:</b> {p.expected ?? "এখনো রেকর্ড হয়নি।"}<En className="text-muted">Recorded result</En></p>
            </Card>
          ))}
        </ul>
      </section>

      <section aria-labelledby="prepared-title" className="space-y-4">
        <H2 id="prepared-title" bn="প্রস্তুত নমুনা কেস" en="Prepared sample cases" line="এগুলো শুধু দেখার জন্য; বদলাতে গেলে বাধা দেওয়া হয়।" />
        <ul className="grid gap-3 sm:grid-cols-2">
          {preparedCases.map((c) => (
            <Card key={c.href} as="li" variant="interactive" href={c.href} title={<>{c.title}<En className="text-muted">{c.en}</En></>} description={c.line}
              meta={<span aria-hidden="true" className="text-accent">→</span>} />
          ))}
        </ul>
      </section>

      <Modal open={!!expected} onClose={() => setExpected(null)} title={expected ? <>প্রত্যাশিত ফল: প্যাক {expected.id}<En className="text-muted">Expected result</En></> : ""}
        description="প্যাকটি অ্যাপে upload করে যে ফল সত্যিই এসেছে, সেটিই এখানে লেখা।">
        {expected && (expected.expected ? (
          <div className="space-y-3 text-sm leading-6">
            <p><b>ঝুঁকির মাত্রা:</b> {expected.expected.risk}</p>
            <ul className="list-disc space-y-1 pl-5">{expected.expected.findings.map((f) => <li key={f}>{f}</li>)}</ul>
            {expected.expected.note && <p className="text-muted">{expected.expected.note}</p>}
            <p className="text-xs text-muted">রেকর্ড: {expected.expected.recordedAt}</p>
          </div>
        ) : <p role="status" className="rounded-[var(--radius-control)] bg-warn-bg p-3 text-sm text-warn">এই প্যাকের ফল এখনো রেকর্ড করা হয়নি।<En>Not recorded yet.</En></p>)}
      </Modal>
      <Modal open={!!progress} onClose={() => undefined} title={progress?.title ?? ""} description="অনুগ্রহ করে অপেক্ষা করুন; কাজ শেষ হলে কেসটি খুলবে।">
        <p role="status" className="flex items-center gap-3 text-sm"><span aria-hidden="true" className="h-4 w-4 animate-spin rounded-full border-2 border-accent border-t-transparent" />{progress?.text}</p>
      </Modal>
    </div>
  );
}
