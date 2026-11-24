"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { demoPacks, demoPlots, preparedCases, type DemoPack } from "@/lib/demo-packs";
import { Card } from "@/components/ui/Card";
import { Modal } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";
import { startTour } from "@/components/GuidedTour";
import { bnDigits } from "@/lib/digits";
import { useLang } from "@/lib/lang";

const btn = "inline-flex min-h-11 flex-col justify-center rounded-[var(--radius-control)] px-3 py-1 text-sm font-semibold";
const primary = `${btn} bg-accent text-white shadow-rest hover:shadow-raised disabled:opacity-60`;
const ghost = `${btn} border border-line bg-surface text-ink hover:bg-bg`;
const bnNum = bnDigits;
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function H2({ id, bn, en, line }: { id: string; bn: string; en: string; line?: string }) {
  const lang = useLang();
  return (
    <div>
      <h2 id={id} className="font-heading text-2xl font-bold text-ink">{lang === "en" ? en : bn}</h2>
      {line && <p className="mt-1 text-sm leading-6 text-muted">{line}</p>}
    </div>
  );
}

export default function DemoPage() {
  const en = useLang() === "en";
  const t = (b: string, e: string) => (en ? e : b);
  const router = useRouter();
  const toast = useToast();
  const [expected, setExpected] = useState<DemoPack | null>(null);
  const [progress, setProgress] = useState<{ title: string; text: string } | null>(null);

  // One click: new case from the pack -> wait for every page to be read -> check -> open at the findings.
  const packCase = async (pack: DemoPack) => {
    setProgress({ title: en ? pack.en : pack.title, text: t("নতুন কেস তৈরি হচ্ছে…", "Creating a new case…") });
    try {
      const land = await api.demoPackCase(pack.id);
      for (let tries = 0; tries < 120; tries++) {
        const docs = await api.getLandDocuments(land.id);
        const done = docs.filter((d) => d.status === "done" || d.status === "failed").length;
        setProgress({ title: en ? pack.en : pack.title, text: en ? `Reading documents: ${done} / ${docs.length}` : `নথি পড়া হচ্ছে: ${bnNum(done)} / ${bnNum(docs.length)}` });
        if (docs.length && done === docs.length) {
          if (docs.some((d) => d.status === "failed")) toast("bad", t("কিছু নথি পড়া যায়নি; কেসে গিয়ে আবার চেষ্টা করুন।", "Some documents could not be read; open the case and try again."));
          break;
        }
        await sleep(3000);
      }
      setProgress({ title: en ? pack.en : pack.title, text: t("কাগজগুলো মিলিয়ে দেখা হচ্ছে…", "Cross-checking the papers…") });
      await api.assessLand(land.id).catch(() => undefined);
      setProgress(null);
      toast("ok", t("আপনার নতুন কেস তৈরি হয়েছে।", "Your new case is ready."));
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
    setProgress({ title, text: t("প্লটসহ নতুন কেস তৈরি হচ্ছে…", "Creating a new case with the plot…") });
    try {
      const land = await api.demoPlotCase(plotId);
      try { await api.startSatelliteCheck(land.id); toast("info", t("স্যাটেলাইট যাচাই শুরু হয়েছে; কয়েক মিনিট লাগতে পারে।", "Satellite check started; it may take a few minutes.")); }
      catch (e) { toast("bad", e instanceof Error ? e.message : t("যাচাই শুরু করা যায়নি।", "Could not start the check.")); }
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
    } catch { toast("bad", t("GeoJSON নামানো যায়নি।", "Could not download the GeoJSON.")); }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-10 pb-10">
      <header className="hero-glow space-y-3">
        <p className="text-sm font-semibold text-accent">{t("বিচারকদের জন্য", "For judges")}</p>
        <h1 className="font-heading text-4xl font-bold text-ink sm:text-5xl">{t("নমুনা ডেটা", "Demo data")}</h1>
        <p className="max-w-2xl text-base leading-7 text-muted">{t("সব নথি কৃত্রিম, “নমুনা / SAMPLE” ছাপ দেওয়া; আসল কারো নাম বা নম্বর নেই। এক ক্লিকে আপনার নিজের নতুন কেস তৈরি হয়, প্রস্তুত নমুনা কেস বদলায় না।", "All documents are synthetic and watermarked. One click makes your own new case; prepared samples never change.")}</p>
      </header>

      <section aria-labelledby="packs-title" className="space-y-4">
        <H2 id="packs-title" bn="নথির নমুনা প্যাক" en="Document packs" line={t("প্রতিটি প্যাকে খতিয়ান, দলিল ও নামজারি (ডি-তে ওয়ারিশ সনদও)।", "Each pack has a khatian, deed and mutation (D also has an heir certificate).")} />
        <ul className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {demoPacks.map((p, i) => (
            <Card key={p.id} as="li" className="animate-fade-up flex flex-col" style={{ "--i": i } as React.CSSProperties}
              icon={<span aria-hidden="true" className="inline-flex h-11 w-11 items-center justify-center rounded-[var(--radius-control)] bg-gradient-to-br from-accent-soft to-surface font-mono text-lg font-bold text-accent shadow-rest">{p.id}</span>}
              title={en ? p.en : p.title} titleAs="h3"
              description={en ? p.showsEn : p.shows}
              footer={<div className="flex flex-wrap gap-2">
                <button type="button" aria-haspopup="dialog" onClick={() => setExpected(p)} className={ghost}>{t("প্রত্যাশিত ফল", "Expected result")}</button>
                <a href={`/api/demo/packs/${p.id}.zip`} download className={ghost}>{t("ফাইল ডাউনলোড", "Download (ZIP)")}</a>
                <button type="button" onClick={() => void packCase(p)} disabled={!!progress} className={primary}>{t("এক ক্লিকে কেস তৈরি", "One-click case")}</button>
              </div>} />
          ))}
        </ul>
      </section>

      <section aria-labelledby="plots-title" className="space-y-4">
        <H2 id="plots-title" bn="স্যাটেলাইট নমুনা প্লট" en="Satellite demo plots" line={t("লাইভ যাচাই এক ঘণ্টায় সর্বোচ্চ ৫টি; একটিতে কয়েক মিনিট লাগে।", "At most 5 live checks per hour; each takes a few minutes.")} />
        <ul className="grid gap-4 md:grid-cols-2">
          {demoPlots.map((p) => (
            <Card key={p.id} as="li" variant="satellite" title={en ? p.en : p.title} titleAs="h3" description={en ? p.showsEn : p.shows}
              footer={<div className="flex flex-wrap gap-2">
                {p.caseHref && <Link href={p.caseHref} className={ghost}>{t("ম্যাপে দেখুন", "View on map")}</Link>}
                <button type="button" onClick={() => void plotCase(p.id, p.title)} disabled={!!progress} className={`${btn} bg-sat text-white shadow-rest disabled:opacity-60`}>{t("এই প্লট দিয়ে যাচাই করুন", "Run a live check")}</button>
                <button type="button" onClick={() => void geojson(p.id)} className={ghost}>{t("GeoJSON", "Download outline")}</button>
              </div>}>
              <p className="rounded-[var(--radius-control)] bg-sat-soft/60 p-3 text-sm leading-6 text-ink"><b>{t("রেকর্ড করা ফল:", "Recorded result:")}</b> {(en ? p.expectedEn : p.expected) ?? t("এখনো রেকর্ড হয়নি।", "Not recorded yet.")}</p>
            </Card>
          ))}
        </ul>
      </section>

      <section aria-labelledby="prepared-title" className="space-y-4">
        <H2 id="prepared-title" bn="প্রস্তুত নমুনা কেস" en="Prepared sample cases" line={t("এগুলো শুধু দেখার জন্য; বদলাতে গেলে বাধা দেওয়া হয়।", "These are view-only; changes are blocked.")} />
        <ul className="grid gap-3 sm:grid-cols-2">
          {preparedCases.map((c) => (
            <Card key={c.href} as="li" variant="interactive" href={c.href} title={en ? c.en : c.title} description={en ? c.lineEn : c.line}
              meta={<span aria-hidden="true" className="text-accent">→</span>} />
          ))}
        </ul>
      </section>

      <Modal open={!!expected} onClose={() => setExpected(null)} title={expected ? (en ? `Expected result: pack ${expected.id}` : `প্রত্যাশিত ফল: প্যাক ${expected.id}`) : ""}
        description={t("প্যাকটি অ্যাপে upload করে যে ফল সত্যিই এসেছে, সেটিই এখানে লেখা।", "This is the result that actually came back when the pack was uploaded to the app.")}>
        {expected && (expected.expected ? (
          <div className="space-y-3 text-sm leading-6">
            <p><b>{t("ঝুঁকির মাত্রা:", "Risk level:")}</b> {expected.expected.risk}</p>
            <ul className="list-disc space-y-1 pl-5">{expected.expected.findings.map((f) => <li key={f}>{f}</li>)}</ul>
            {expected.expected.note && <p className="text-muted">{expected.expected.note}</p>}
            <p className="text-xs text-muted">{t("রেকর্ড", "Recorded")}: {expected.expected.recordedAt}</p>
          </div>
        ) : <p role="status" className="rounded-[var(--radius-control)] bg-warn-bg p-3 text-sm text-warn">{t("এই প্যাকের ফল এখনো রেকর্ড করা হয়নি।", "Not recorded yet.")}</p>)}
      </Modal>
      <Modal open={!!progress} onClose={() => undefined} title={progress?.title ?? ""} description={t("অনুগ্রহ করে অপেক্ষা করুন; কাজ শেষ হলে কেসটি খুলবে।", "Please wait; the case opens when it is done.")}>
        <p role="status" className="flex items-center gap-3 text-sm"><span aria-hidden="true" className="h-4 w-4 animate-spin rounded-full border-2 border-accent border-t-transparent" />{progress?.text}</p>
      </Modal>
    </div>
  );
}
