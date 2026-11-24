import type { Metadata } from "next";
import Link from "next/link";
import { Card, IconTile } from "@/components/ui/Card";
import { T } from "@/lib/lang";
import { Term } from "@/components/ui/Term";
import { BholaPreview } from "@/components/BholaPreview";
import { glossary } from "@/lib/glossary";
import { limits, satelliteFindings } from "@/lib/explain";

export const metadata: Metadata = { title: "কীভাবে কাজ করে · How it works · JomiGuard Sentinel" };

const CASE_00001 = "/cases/66c09208-d737-59f0-937e-de349f50899a";
const BHOLA = "/cases/3122299c-4917-5c21-827d-598119df27ef";

function H2({ id, bn, en }: { id: string; bn: string; en: string }) {
  return <h2 id={id} className="scroll-mt-40 font-heading text-2xl font-bold text-ink sm:text-3xl"><T bn={bn} en={en} /></h2>;
}

/** A row of boxes joined by arrows; wraps to a column on phones. Each box fades in after the last. */
function Flow({ steps, sat = false }: { steps: [string, string][]; sat?: boolean }) {
  return (
    <ol className="flex flex-col items-stretch gap-2 lg:flex-row lg:items-center">
      {steps.map(([bnText, en], i) => (
        <li key={en} className="animate-fade-up flex flex-col items-center gap-2 lg:flex-1 lg:flex-row" style={{ "--i": i } as React.CSSProperties}>
          <span className={`w-full rounded-[var(--radius-control)] border bg-surface px-3 py-2.5 text-center text-sm font-semibold leading-snug shadow-rest ${sat ? "border-sat/30" : "border-accent/25"}`}>
            <span className={`mb-1 inline-flex h-6 w-6 items-center justify-center rounded-full text-xs text-surface ${sat ? "bg-sat" : "bg-accent"}`}><T bn={"১২৩৪৫৬"[i]} en={String(i + 1)} /></span>
            <span className="block text-ink"><T bn={bnText} en={en} /></span>
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
        <p className="text-sm font-semibold text-accent"><T bn={"সহজ ভাষায়"} en={"In plain words"} /></p>
        <h1 className="font-heading text-4xl font-bold leading-tight text-ink sm:text-5xl"><T bn={"কীভাবে কাজ করে"} en={"How it works"} /></h1>
        <p className="max-w-2xl text-base leading-7 text-muted"><T bn={"জমি কেনার আগে দুইবার যাচাই: কাগজে কাগজে মিল আছে কি না, আর কাগজের সঙ্গে মাটির মিল আছে কি না।"} en={"Two checks before buying: do the papers agree, and do the papers match the ground?"} /></p>
        <nav aria-label="Sections of this page" className="flex flex-wrap gap-2 pt-1 text-sm">
          {[["problem", "সমস্যা", "Problem"], ["two-checks", "দুইবার যাচাই", "Two checks"], ["paper", "কাগজ যাচাই", "Paper check"], ["ground", "মাটি যাচাই", "Ground check"], ["paper-vs-ground", "কাগজ বনাম মাটি", "Paper vs ground"], ["limits", "যা বলে না", "Limits"], ["glossary", "শব্দকোষ", "Glossary"]].map(([id, label, labelEn]) => (
            <a key={id} href={`#${id}`} className="inline-flex min-h-11 items-center rounded-full border border-edge bg-surface px-4 font-semibold text-accent shadow-rest hover:shadow-raised"><T bn={label} en={labelEn} /></a>
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
              <li key={e} className="flex gap-3"><span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-bad-bg font-bold text-bad"><T bn={"১২৩"[i]} en={String(i + 1)} /></span><p className="text-sm leading-6 text-ink"><T bn={b} en={e} /></p></li>
            ))}
          </ol>
          <svg viewBox="0 0 240 150" role="img" aria-label="Land on paper, water on the ground" className="mx-auto w-full max-w-[15rem]">
            <rect x="12" y="14" width="96" height="122" rx="10" className="fill-accent-soft stroke-accent" strokeWidth="2" />
            {[38, 56, 74, 92].map((y) => <line key={y} x1="28" x2="92" y1={y} y2={y} className="stroke-accent" strokeWidth="3" strokeLinecap="round" opacity=".45" />)}
            <text x="60" y="122" textAnchor="middle" className="fill-accent" fontSize="13" fontWeight="700"><T bn="নাল" en="Nal" /></text>
            <text x="120" y="80" textAnchor="middle" className="fill-gold" fontSize="22" fontWeight="700">≠</text>
            <rect x="132" y="14" width="96" height="122" rx="10" className="fill-sat-soft stroke-sat" strokeWidth="2" />
            <path d="M140 92 q12 -10 24 0 t24 0 t24 0 t12 0 M140 110 q12 -10 24 0 t24 0 t24 0 t12 0" className="stroke-sat" strokeWidth="3" fill="none" strokeLinecap="round" />
            <text x="180" y="52" textAnchor="middle" className="fill-sat" fontSize="13" fontWeight="700"><T bn="পানি" en="Water" /></text>
          </svg>
        </div>
      </Card>

      {/* 2b */}
      <Card as="section" aria-labelledby="two-checks" className="space-y-5">
        <H2 id="two-checks" bn="দুইবার যাচাই" en="Two checks" />
        <div className="grid items-center gap-3 md:grid-cols-[1fr_auto_1fr_auto_1fr]">
          <div className="grid gap-3">
            <div className="rounded-[var(--radius-control)] border border-accent/25 bg-accent-soft/60 p-4 text-center"><IconTile>{icon("M6 3.75h8l4 4v12.5H6z M14 3.75v4h4 M9 12h6 M9 15.5h6")}</IconTile><p className="mt-2 font-semibold text-ink"><T bn={"কাগজ যাচাই"} en={"Paper check"} /></p><p className="mt-1 text-xs text-muted"><T bn={"খতিয়ান, দলিল, নামজারি, ওয়ারিশ সনদ"} en={"Khatian, deed, mutation, heir certificate"} /></p></div>
            <div className="rounded-[var(--radius-control)] border border-sat/30 bg-sat-soft/60 p-4 text-center"><IconTile satellite>{icon("M4 18 9 9l4 6 3-4 4 7z M16 6.5a2 2 0 1 0 0-.01")}</IconTile><p className="mt-2 font-semibold text-ink"><T bn={"মাটি যাচাই"} en={"Ground check (satellite)"} /></p><p className="mt-1 text-xs text-muted"><T bn={"২০১৯–২০২৫, প্রতি ফেব্রুয়ারি"} en={"2019–2025, every February"} /></p></div>
          </div>
          <span aria-hidden="true" className="text-center text-2xl text-accent"><span className="md:hidden">↓</span><span className="hidden md:inline">→</span></span>
          <div className="rounded-[var(--radius-control)] border border-gold/40 bg-surface p-4 text-center shadow-rest"><p className="font-semibold text-ink"><T bn={"কাগজ বনাম মাটি"} en={"Paper vs ground"} /></p><p className="mt-1 text-xs leading-5 text-muted"><T bn={"খতিয়ানের জমির শ্রেণী আর ছবিতে দেখা পানি/গাছ মেলানো"} en={"Compare the khatian land class with the water and trees seen in images"} /></p></div>
          <span aria-hidden="true" className="text-center text-2xl text-accent"><span className="md:hidden">↓</span><span className="hidden md:inline">→</span></span>
          <div className="rounded-[var(--radius-control)] bg-gradient-to-br from-accent to-sat p-4 text-center text-white shadow-raised"><p className="font-semibold"><T bn={"রিপোর্ট"} en={"Report"} /></p><p className="mt-1 text-xs leading-5 opacity-90"><T bn={"কী মিলেছে, কী মেলেনি, এরপর কী করবেন"} en={"What matched, what did not, what to do next"} /></p></div>
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
        <p className="text-sm leading-6 text-muted"><T bn={<>এক্সট্র্যাক্টর শুধু ছাপা লেখা তোলে, কোনো হিসাব করে না; একক বদল ও হিসাব আলাদা ধাপে হয়, আর প্রতিটি সংখ্যার পাশে ছাপা লেখাটিও রাখা হয়। <Term t="শতাংশ" /> ছাড়া অন্য একক (বিঘা, কাঠা) আন্দাজে বদলানো হয় না।</>} en={<>The extractor copies printed text only; arithmetic and unit conversion happen later, and the printed text stays next to every number. Units other than <Term t="শতাংশ">shatangsho</Term> (bigha, katha) are never converted by guesswork.</>} /></p>
        <Card variant="highlight" tone="bad" title={<><T bn={"উদাহরণ: কেস ০০০০১"} en={"Worked example: case 00001 (synthetic)"} /></>} titleAs="h3">
          <p className="text-sm font-semibold text-ink"><T bn={"অংশের চেয়ে বেশি জমি হস্তান্তর"} en={"More land transferred than the seller's share"} /></p>
          <p className="text-sm leading-6 text-ink"><T bn={<><Term t="খতিয়ান" />-এ <Term t="দাগ" /> ২৬৭৯-এ বিক্রেতার অংশ ৪.৭৯৫ শতাংশ, কিন্তু <Term t="দলিল" />-এ ১৮ শতাংশ হস্তান্তর করা হচ্ছে। অতিরিক্ত ১৩.২০৫ শতাংশের মালিকানা যাচাই করতে বলা হয়।</>} en={<>On the <Term t="খতিয়ান">khatian</Term>, the seller holds 4.795 shatangsho of <Term t="দাগ">dag</Term> 2679, but the <Term t="দলিল">deed</Term> transfers 18. The app asks you to check who owns the extra 13.205 shatangsho.</>} /></p>
          <p className="text-xs leading-5 text-muted"><T bn={"এই কেসের ঝুঁকির মাত্রা: উচ্চ ঝুঁকি। উৎস: খতিয়ানের মালিকের অংশ ও দলিলের তফসিলের পরিমাণ।"} en={"Risk level for this case: high. Source: the owner's share on the khatian and the schedule area on the deed."} /></p>
          <Link href={CASE_00001} className="inline-flex min-h-11 flex-col justify-center text-sm font-semibold text-accent underline underline-offset-4"><T bn={"কেসটি খুলুন →"} en={"Open the case"} /></Link>
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
        <p className="text-sm leading-6 text-muted"><T bn={"প্রবণতা মাপা হয় Theil-Sen ঢাল দিয়ে (সব বছর-জোড়ার ঢালের মধ্যমা)। অস্বাভাবিক বছর (outlier) আর কম পরিষ্কার ছবির বছর (low-confidence) প্রবণতা থেকে বাদ যায়; স্থায়ী বদল ধরতে অন্তত ৪টি পরিষ্কার বছর লাগে।"} en={"Trends use the Theil-Sen slope; outlier and low-confidence years are left out; a lasting change needs at least 4 clean years."} /></p>
        <div className="grid items-center gap-5 md:grid-cols-[1fr_1fr]">
          <div className="space-y-2 text-sm leading-6 text-ink">
            <h3 className="font-semibold"><T bn={"উদাহরণ: ভোলা, চর মেঘনা, দাগ ৪১৭"} en={"Worked example: the Bhola case (synthetic papers, real satellite result)"} /></h3>
            <p><T bn={"খতিয়ানে জমির শ্রেণী “নাল” (চাষের জমি)। ফেব্রুয়ারিতে প্লটের আশেপাশে পানি ছিল ২০১৯-এ ২৮.১%, ২০২৫-এ ৬৫.০%; প্রবণতা প্রতি বছর প্রায় ৫.১ শতাংশ-বিন্দু বেড়েছে।"} en={"The khatian class is “nal” (cropland). In February, water around the plot was 28.1% in 2019 and 65.0% in 2025; the trend rose about 5.1 percentage points a year."} /></p>
            <p><T bn={"ফলাফল: (a) শুকনো মৌসুমেও পানি, (g) পানি বছর বছর বাড়ছে, (d) কাগজে চাষের জমি, ছবিতে পানি।"} en={"Findings: (a) water even in the dry season, (g) water rising year by year, (d) cropland on paper, water in the images."} /></p>
            <Link href={BHOLA} className="inline-flex min-h-11 flex-col justify-center font-semibold text-sat underline underline-offset-4"><T bn={"কেসটি খুলুন →"} en={"Open the case"} /></Link>
          </div>
          <BholaPreview />
        </div>
      </Card>

      {/* 2e */}
      <Card as="section" aria-labelledby="paper-vs-ground" className="space-y-4">
        <H2 id="paper-vs-ground" bn="কাগজ বনাম মাটি: স্যাটেলাইটের ফলাফল" en="Paper vs ground: satellite findings" />
        <p className="text-sm leading-6 text-muted"><T bn={"স্যাটেলাইটের ফলাফল আলাদা অংশে দেখানো হয়; কাগজের ঝুঁকির মাত্রা এতে বদলায় না।"} en={"Satellite findings are a separate group and never change the document risk level."} /></p>
        <ul className="grid gap-3 md:grid-cols-2">
          {satelliteFindings.map((f) => (
            <Card key={f.letter} as="li" variant="highlight" tone={f.letter === "f" ? "info" : "warn"} className="!p-4"
              title={<span className="flex items-start gap-2"><span className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-sat font-mono text-sm text-surface">{f.letter}</span><span><T bn={f.title} en={f.en} /></span></span>} titleAs="h3">
              <p className="text-sm leading-6"><b><T bn="কখন:" en="When:" /></b> <T bn={f.trigger} en={f.triggerEn} /></p>
              <p className="text-sm leading-6"><b><T bn="এরপর:" en="Next:" /></b> <T bn={f.next} en={f.nextEn} /></p>
            </Card>
          ))}
        </ul>
      </Card>

      {/* 2f */}
      <Card as="section" aria-labelledby="limits" className="space-y-4 !border-gold/40">
        <H2 id="limits" bn="যা এই অ্যাপ বলে না" en="What it does NOT tell you" />
        <ul className="space-y-2">
          {limits.map(([b, e]) => <li key={e} className="flex gap-3 rounded-[var(--radius-control)] bg-warn-bg/60 p-3 text-sm leading-6 text-ink"><span aria-hidden="true" className="font-bold text-warn">!</span><span><T bn={b} en={e} /></span></li>)}
        </ul>
      </Card>

      {/* 2g */}
      <Card as="section" aria-labelledby="glossary" className="space-y-4">
        <H2 id="glossary" bn="শব্দকোষ" en="Glossary" />
        <dl className="grid gap-3 sm:grid-cols-2">
          {glossary.map((g) => (
            <div key={g.term} className="rounded-[var(--radius-control)] border border-edge bg-bg/60 p-3">
              <dt className="font-semibold text-ink">{g.term} <span lang="en" className="text-sm font-normal text-muted">· {g.latin}</span></dt>
              <dd className="mt-1 text-sm leading-6 text-ink"><T bn={g.bn} en={g.en} /></dd>
            </div>
          ))}
        </dl>
      </Card>
    </div>
  );
}
