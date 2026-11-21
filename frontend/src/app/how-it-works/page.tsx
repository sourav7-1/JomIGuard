import type { Metadata } from "next";
import Link from "next/link";
import { Card, IconTile } from "@/components/ui/Card";
import { En } from "@/components/ui/En";
import { Term } from "@/components/ui/Term";
import { BholaPreview } from "@/components/BholaPreview";
import { glossary } from "@/lib/glossary";
import { limits, satelliteFindings } from "@/lib/explain";

export const metadata: Metadata = { title: "কীভাবে কাজ করে · JomiGuard Sentinel" };

const CASE_00001 = "/cases/66c09208-d737-59f0-937e-de349f50899a";
const BHOLA = "/cases/3122299c-4917-5c21-827d-598119df27ef";

function H2({ id, bn, en }: { id: string; bn: string; en: string }) {
  return <h2 id={id} className="scroll-mt-40 font-heading text-2xl font-bold text-ink sm:text-3xl">{bn}<En className="mt-0.5 text-sm text-muted">{en}</En></h2>;
}

/** A row of boxes joined by arrows; wraps to a column on phones. Each box fades in after the last. */
function Flow({ steps, sat = false }: { steps: [string, string][]; sat?: boolean }) {
  return (
    <ol className="flex flex-col items-stretch gap-2 lg:flex-row lg:items-center">
      {steps.map(([bnText, en], i) => (
        <li key={en} className="animate-fade-up flex flex-col items-center gap-2 lg:flex-1 lg:flex-row" style={{ "--i": i } as React.CSSProperties}>
          <span className={`w-full rounded-[var(--radius-control)] border bg-surface px-3 py-2.5 text-center text-sm font-semibold leading-snug shadow-rest ${sat ? "border-sat/30" : "border-accent/25"}`}>
            <span className={`mb-1 inline-flex h-6 w-6 items-center justify-center rounded-full text-xs text-surface ${sat ? "bg-sat" : "bg-accent"}`}>{"১২৩৪৫৬"[i]}</span>
            <span className="block text-ink">{bnText}</span><En className="text-muted">{en}</En>
          </span>
          {i < steps.length - 1 && <span aria-hidden="true" className={`text-lg ${sat ? "text-sat" : "text-accent"} lg:-mx-1`}><span className="lg:hidden">↓</span><span className="hidden lg:inline">→</span></span>}
        </li>
      ))}
    </ol>
  );
}

const icon = (d: string) => <svg viewBox="0 0 24 24" fill="none" className="h-6 w-6"><path d={d} stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></svg>;

export default function HowItWorksPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-10 pb-10">
      <header className="hero-glow space-y-3">
        <p className="text-sm font-semibold text-accent">সহজ ভাষায়<En>In plain words</En></p>
        <h1 className="font-heading text-4xl font-bold leading-tight text-ink sm:text-5xl">কীভাবে কাজ করে<En className="mt-1 text-base text-muted">How it works</En></h1>
        <p className="max-w-2xl text-base leading-7 text-muted">জমি কেনার আগে দুইবার যাচাই: কাগজে কাগজে মিল আছে কি না, আর কাগজের সঙ্গে মাটির মিল আছে কি না।<En>Two checks before buying: do the papers agree, and do the papers match the ground?</En></p>
        <nav aria-label="এই পাতার অংশ" className="flex flex-wrap gap-2 pt-1 text-sm">
          {[["problem", "সমস্যা"], ["two-checks", "দুইবার যাচাই"], ["paper", "কাগজ যাচাই"], ["ground", "মাটি যাচাই"], ["paper-vs-ground", "কাগজ বনাম মাটি"], ["limits", "যা বলে না"], ["glossary", "শব্দকোষ"]].map(([id, label]) => (
            <a key={id} href={`#${id}`} className="inline-flex min-h-11 items-center rounded-full border border-edge bg-surface px-4 font-semibold text-accent shadow-rest hover:shadow-raised">{label}</a>
          ))}
        </nav>
      </header>

      {/* 2a */}
      <Card as="section" aria-labelledby="problem" className="space-y-5">
        <H2 id="problem" bn="সমস্যা" en="The problem" />
        <div className="grid items-center gap-6 md:grid-cols-[1fr_15rem]">
          <ol className="space-y-3">
            {[
              ["কাগজের ফাঁদ: এক জনের অংশের চেয়ে বেশি জমি বিক্রি, ভুল দাগ বা খতিয়ান নম্বর, নামজারিতে ওয়ারিশ বাদ।", "Paper traps: selling more than one's share, wrong plot numbers, heirs left out."],
              ["মাটির ঝুঁকি: কাগজে চাষের জমি, কিন্তু মাঠে পানি বা নদীভাঙন।", "Ground risks: farmland on paper, water or river erosion on the ground."],
              ["সাধারণ ক্রেতা এর কোনোটাই নিজে সহজে যাচাই করতে পারেন না।", "Ordinary buyers cannot easily check either."],
            ].map(([b, e], i) => (
              <li key={e} className="flex gap-3"><span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-bad-bg font-bold text-bad">{"১২৩"[i]}</span><p className="text-sm leading-6 text-ink">{b}<En className="text-muted">{e}</En></p></li>
            ))}
          </ol>
          <svg viewBox="0 0 240 150" role="img" aria-label="কাগজে জমি, মাঠে পানি" className="mx-auto w-full max-w-[15rem]">
            <rect x="12" y="14" width="96" height="122" rx="10" className="fill-accent-soft stroke-accent" strokeWidth="2" />
            {[38, 56, 74, 92].map((y) => <line key={y} x1="28" x2="92" y1={y} y2={y} className="stroke-accent" strokeWidth="3" strokeLinecap="round" opacity=".45" />)}
            <text x="60" y="122" textAnchor="middle" className="fill-accent" fontSize="13" fontWeight="700">নাল</text>
            <text x="120" y="80" textAnchor="middle" className="fill-gold" fontSize="22" fontWeight="700">≠</text>
            <rect x="132" y="14" width="96" height="122" rx="10" className="fill-sat-soft stroke-sat" strokeWidth="2" />
            <path d="M140 92 q12 -10 24 0 t24 0 t24 0 t12 0 M140 110 q12 -10 24 0 t24 0 t24 0 t12 0" className="stroke-sat" strokeWidth="3" fill="none" strokeLinecap="round" />
            <text x="180" y="52" textAnchor="middle" className="fill-sat" fontSize="13" fontWeight="700">পানি</text>
          </svg>
        </div>
      </Card>

      {/* 2b */}
      <Card as="section" aria-labelledby="two-checks" className="space-y-5">
        <H2 id="two-checks" bn="দুইবার যাচাই" en="Two checks" />
        <div className="grid items-center gap-3 md:grid-cols-[1fr_auto_1fr_auto_1fr]">
          <div className="grid gap-3">
            <div className="rounded-[var(--radius-control)] border border-accent/25 bg-accent-soft/60 p-4 text-center"><IconTile>{icon("M6 3.75h8l4 4v12.5H6z M14 3.75v4h4 M9 12h6 M9 15.5h6")}</IconTile><p className="mt-2 font-semibold text-ink">কাগজ যাচাই<En className="text-muted">Paper check</En></p><p className="mt-1 text-xs text-muted">খতিয়ান, দলিল, নামজারি, ওয়ারিশ সনদ</p></div>
            <div className="rounded-[var(--radius-control)] border border-sat/30 bg-sat-soft/60 p-4 text-center"><IconTile satellite>{icon("M4 18 9 9l4 6 3-4 4 7z M16 6.5a2 2 0 1 0 0-.01")}</IconTile><p className="mt-2 font-semibold text-ink">মাটি যাচাই<En className="text-muted">Ground check (satellite)</En></p><p className="mt-1 text-xs text-muted">২০১৯–২০২৫, প্রতি ফেব্রুয়ারি</p></div>
          </div>
          <span aria-hidden="true" className="text-center text-2xl text-accent"><span className="md:hidden">↓</span><span className="hidden md:inline">→</span></span>
          <div className="rounded-[var(--radius-control)] border border-gold/40 bg-surface p-4 text-center shadow-rest"><p className="font-semibold text-ink">কাগজ বনাম মাটি<En className="text-muted">Paper vs ground</En></p><p className="mt-1 text-xs leading-5 text-muted">খতিয়ানের জমির শ্রেণী আর ছবিতে দেখা পানি/গাছ মেলানো</p></div>
          <span aria-hidden="true" className="text-center text-2xl text-accent"><span className="md:hidden">↓</span><span className="hidden md:inline">→</span></span>
          <div className="rounded-[var(--radius-control)] bg-gradient-to-br from-accent to-sat p-4 text-center text-white shadow-raised"><p className="font-semibold">রিপোর্ট<En>Report</En></p><p className="mt-1 text-xs leading-5 opacity-90">কী মিলেছে, কী মেলেনি, এরপর কী করবেন</p></div>
        </div>
      </Card>

      {/* 2c */}
      <Card as="section" aria-labelledby="paper" className="space-y-5">
        <H2 id="paper" bn="কাগজ যাচাই, ধাপে ধাপে" en="Paper check, step by step" />
        <Flow steps={[
          ["নথি upload", "Upload documents"],
          ["OCR / vision LLM ছাপা লেখা পড়ে", "OCR or a vision LLM reads the printed text"],
          ["বাংলা অঙ্ক, একক, নাম একরূপ করা", "Normalise Bangla digits, units, names"],
          ["১৩টি নিয়মে কাগজগুলো মেলানো", "13 rules compare the papers"],
          ["অমিল, উৎসের ঘর চিহ্নিত", "Findings with the source field highlighted"],
        ]} />
        <p className="text-sm leading-6 text-muted">এক্সট্র্যাক্টর শুধু ছাপা লেখা তোলে, কোনো হিসাব করে না; একক বদল ও হিসাব আলাদা ধাপে হয়, আর প্রতিটি সংখ্যার পাশে ছাপা লেখাটিও রাখা হয়। <Term t="শতাংশ" /> ছাড়া অন্য একক (বিঘা, কাঠা) আন্দাজে বদলানো হয় না।<En>The extractor copies printed text only; arithmetic and unit conversion happen later, and the printed text stays next to every number.</En></p>
        <Card variant="highlight" tone="bad" title={<>উদাহরণ: কেস ০০০০১<En className="text-muted">Worked example: case 00001 (synthetic)</En></>} titleAs="h3">
          <p className="text-sm font-semibold text-ink">অংশের চেয়ে বেশি জমি হস্তান্তর</p>
          <p className="text-sm leading-6 text-ink"><Term t="খতিয়ান" />-এ <Term t="দাগ" /> ২৬৭৯-এ বিক্রেতার অংশ ৪.৭৯৫ শতাংশ, কিন্তু <Term t="দলিল" />-এ ১৮ শতাংশ হস্তান্তর করা হচ্ছে। অতিরিক্ত ১৩.২০৫ শতাংশের মালিকানা যাচাই করতে বলা হয়।<En className="text-muted">The seller holds 4.795 decimals on the khatian but the deed transfers 18.</En></p>
          <p className="text-xs leading-5 text-muted">এই কেসের ঝুঁকির মাত্রা: উচ্চ ঝুঁকি। উৎস: খতিয়ানের মালিকের অংশ ও দলিলের তফসিলের পরিমাণ।</p>
          <Link href={CASE_00001} className="inline-flex min-h-11 flex-col justify-center text-sm font-semibold text-accent underline underline-offset-4">কেসটি খুলুন →<En>Open the case</En></Link>
        </Card>
      </Card>

      {/* 2d */}
      <Card as="section" variant="satellite" aria-labelledby="ground" className="space-y-5">
        <H2 id="ground" bn="মাটি যাচাই, ধাপে ধাপে" en="Ground check, step by step" />
        <Flow sat steps={[
          ["মানচিত্রে প্লট আঁকা", "Draw the plot"],
          ["চারপাশে প্রায় ২০০ মিটার", "About 200 m around it"],
          ["২০১৯–২০২৫, প্রতি ফেব্রুয়ারির Sentinel-1/2 ছবি (Google Earth Engine)", "Sentinel-1/2 images, every February 2019–2025"],
          ["আমাদের U-Net ম্যাপ + গাছ-আচ্ছাদন মডেল", "Our U-Net map + tree-cover model"],
          ["পানি/সবুজ/গাছের প্রবণতা, খারাপ বছর বাদ", "Water, green and tree trends; bad years filtered"],
          ["ফলাফল", "Findings"],
        ]} />
        <p className="text-sm leading-6 text-muted">প্রবণতা মাপা হয় Theil-Sen ঢাল দিয়ে (সব বছর-জোড়ার ঢালের মধ্যমা)। অস্বাভাবিক বছর (outlier) আর কম পরিষ্কার ছবির বছর (low-confidence) প্রবণতা থেকে বাদ যায়; স্থায়ী বদল ধরতে অন্তত ৪টি পরিষ্কার বছর লাগে।<En>Trends use the Theil-Sen slope; outlier and low-confidence years are left out; a lasting change needs at least 4 clean years.</En></p>
        <div className="grid items-center gap-5 md:grid-cols-[1fr_1fr]">
          <div className="space-y-2 text-sm leading-6 text-ink">
            <h3 className="font-semibold">উদাহরণ: ভোলা, চর মেঘনা, দাগ ৪১৭<En className="text-muted">Worked example: the Bhola case (synthetic papers, real satellite result)</En></h3>
            <p>খতিয়ানে জমির শ্রেণী “নাল” (চাষের জমি)। ফেব্রুয়ারিতে প্লটের আশেপাশে পানি ছিল ২০১৯-এ ২৮.১%, ২০২৫-এ ৬৫.০%; প্রবণতা প্রতি বছর প্রায় ৫.১ শতাংশ-বিন্দু বেড়েছে।</p>
            <p>ফলাফল: (a) শুকনো মৌসুমেও পানি, (g) পানি বছর বছর বাড়ছে, (d) কাগজে চাষের জমি, ছবিতে পানি।</p>
            <Link href={BHOLA} className="inline-flex min-h-11 flex-col justify-center font-semibold text-sat underline underline-offset-4">কেসটি খুলুন →<En>Open the case</En></Link>
          </div>
          <BholaPreview />
        </div>
      </Card>

      {/* 2e */}
      <Card as="section" aria-labelledby="paper-vs-ground" className="space-y-4">
        <H2 id="paper-vs-ground" bn="কাগজ বনাম মাটি: স্যাটেলাইটের ফলাফল" en="Paper vs ground: satellite findings" />
        <p className="text-sm leading-6 text-muted">স্যাটেলাইটের ফলাফল আলাদা অংশে দেখানো হয়; কাগজের ঝুঁকির মাত্রা এতে বদলায় না।<En>Satellite findings are a separate group and never change the document risk level.</En></p>
        <ul className="grid gap-3 md:grid-cols-2">
          {satelliteFindings.map((f) => (
            <Card key={f.letter} as="li" variant="highlight" tone={f.letter === "f" ? "info" : "warn"} className="!p-4"
              title={<span className="flex items-start gap-2"><span className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-sat font-mono text-sm text-surface">{f.letter}</span><span>{f.title}<En className="text-muted">{f.en}</En></span></span>} titleAs="h3">
              <p className="text-sm leading-6"><b>কখন:</b> {f.trigger}</p>
              <p className="text-sm leading-6"><b>এরপর:</b> {f.next}</p>
            </Card>
          ))}
        </ul>
      </Card>

      {/* 2f */}
      <Card as="section" aria-labelledby="limits" className="space-y-4 !border-gold/40">
        <H2 id="limits" bn="যা এই অ্যাপ বলে না" en="What it does NOT tell you" />
        <ul className="space-y-2">
          {limits.map(([b, e]) => <li key={e} className="flex gap-3 rounded-[var(--radius-control)] bg-warn-bg/60 p-3 text-sm leading-6 text-ink"><span aria-hidden="true" className="font-bold text-warn">!</span><span>{b}<En className="text-muted">{e}</En></span></li>)}
        </ul>
      </Card>

      {/* 2g */}
      <Card as="section" aria-labelledby="glossary" className="space-y-4">
        <H2 id="glossary" bn="শব্দকোষ" en="Glossary" />
        <dl className="grid gap-3 sm:grid-cols-2">
          {glossary.map((g) => (
            <div key={g.term} className="rounded-[var(--radius-control)] border border-edge bg-bg/60 p-3">
              <dt className="font-semibold text-ink">{g.term} <span lang="en" className="text-sm font-normal text-muted">· {g.latin}</span></dt>
              <dd className="mt-1 text-sm leading-6 text-ink">{g.bn}<En className="text-muted">{g.en}</En></dd>
            </div>
          ))}
        </dl>
      </Card>
    </div>
  );
}
