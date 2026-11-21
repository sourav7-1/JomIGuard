import type { Metadata } from "next";
import Image from "next/image";
import { Card } from "@/components/ui/Card";
import { En } from "@/components/ui/En";
import { DocsStatus } from "@/components/DocsStatus";
import { limits } from "@/lib/explain";

export const metadata: Metadata = { title: "ডকস · JomiGuard Sentinel" };

// Every number on this page comes from the repo: sentinel/models/*_report.json, docs/datasets/v1.md,
// and the test runs of 2026-11-20 (backend pytest, ml pytest, sentinel pytest, npm test).
const TOC: [string, string, string][] = [
  ["pitch", "পিচ", "Pitch"], ["tour", "প্রোডাক্ট ট্যুর", "Product tour"], ["architecture", "আর্কিটেকচার", "Architecture"],
  ["ai", "AI ও ডেটা", "AI & data"], ["privacy", "গোপনীয়তা ও দায়িত্বশীল AI", "Privacy & responsible AI"],
  ["roadmap", "অবস্থা ও পরিকল্পনা", "Status & roadmap"], ["team", "টিম ও লিংক", "Team & links"], ["status", "লাইভ অবস্থা", "Live status"],
];

function Section({ id, bn, en, children }: { id: string; bn: string; en: string; children: React.ReactNode }) {
  return (
    <Card as="section" aria-labelledby={id} className="scroll-mt-40 space-y-4">
      <h2 id={id} className="font-heading text-2xl font-bold text-ink sm:text-3xl">{bn}<En className="mt-0.5 text-sm text-muted">{en}</En></h2>
      {children}
    </Card>
  );
}

const Stat = ({ v, bn, en }: { v: string; bn: string; en: string }) => (
  <div className="rounded-[var(--radius-control)] border border-edge bg-bg/60 p-3"><p className="font-mono text-2xl font-bold text-accent">{v}</p><p className="text-sm text-ink">{bn}</p><En className="text-muted">{en}</En></div>
);

const SHOTS: [string, string, string][] = [
  ["home", "মূল পাতা: সেবাসমূহ ও বিচারকদের গাইড", "Home: services and the judge guide"],
  ["tracker", "কেসের অবস্থা: কাগজ থেকে রিপোর্ট পর্যন্ত ৫ ধাপ", "Case tracker: five steps from papers to report"],
  ["findings", "যা মেলেনি: প্রতিটি অমিলের উৎস-বোতাম", "Findings with source links"],
  ["satellite", "স্যাটেলাইট যাচাই: মানচিত্র, চার্ট ও ফলাফল", "Satellite panel: map, charts, findings"],
  ["report", "PDF রিপোর্টের লেখা (যে HTML থেকে PDF তৈরি হয়)", "PDF report content (the HTML the PDF is printed from)"],
];

const ARCH: [string, string, string][] = [
  ["Next.js", "ওয়েব অ্যাপ; ব্রাউজার শুধু /api-তে কথা বলে", "Web app; the browser only talks to /api"],
  ["FastAPI", "API: কেস, নথি, নিয়ম, রিপোর্ট, এসক্রো, গার্ডিয়ান", "API: cases, documents, rules, reports, escrow, guardian"],
  ["PostgreSQL", "কেস, পড়া তথ্য, ফলাফল ও ইতিহাস", "Cases, extracted data, findings, history"],
  ["MinIO", "আপলোড করা নথির ফাইল", "Uploaded document files"],
  ["Redis", "Celery কাজের সারি", "Celery task queues"],
  ["Celery: নথি", "OCR / vision LLM দিয়ে নথি পড়া", "Reads documents with OCR / a vision LLM"],
  ["Celery: স্যাটেলাইট", "আলাদা সারি, একবারে একটি যাচাই", "Own queue, one satellite check at a time"],
  ["Sentinel সার্ভিস", "U-Net + গাছ-আচ্ছাদন মডেল, Google Earth Engine থেকে Sentinel-1/2", "U-Net + tree-cover model, Sentinel-1/2 via Earth Engine"],
];

export default function DocsPage() {
  return (
    <div className="mx-auto max-w-6xl pb-10">
      <header className="hero-glow mb-6 space-y-2">
        <p className="text-sm font-semibold text-accent">পিচ ও টেকনিক্যাল হোয়াইটপেপার<En>Live pitch + technical whitepaper</En></p>
        <h1 className="font-heading text-4xl font-bold text-ink sm:text-5xl">ডকস<En className="mt-1 text-base text-muted">Docs</En></h1>
      </header>
      <div className="lg:grid lg:grid-cols-[14rem_1fr] lg:gap-8">
        <nav aria-label="সূচি (Table of contents)" className="sticky top-[6.1rem] z-20 -mx-4 mb-4 overflow-x-auto [scrollbar-width:none] border-y border-edge bg-bg/90 px-4 py-2 backdrop-blur lg:top-40 lg:mx-0 lg:mb-0 lg:self-start lg:overflow-visible lg:rounded-[var(--radius-card)] lg:border lg:bg-surface lg:p-3 lg:shadow-rest">
          <ol className="flex gap-2 lg:flex-col lg:gap-0.5">
            {TOC.map(([id, bn, en]) => (
              <li key={id} className="shrink-0"><a href={`#${id}`} className="block min-h-11 rounded-[var(--radius-control)] px-3 py-1.5 text-sm font-semibold text-ink hover:bg-accent-soft">{bn}<En className="text-muted">{en}</En></a></li>
            ))}
          </ol>
        </nav>

        <div className="min-w-0 space-y-6">
          <Section id="pitch" bn="পিচ" en="Pitch">
            <p className="text-lg font-semibold leading-8 text-ink">জমি কেনার আগে কাগজ আর মাটি, দুটোই যাচাই: কী মিলেছে, কী মেলেনি, এরপর কী করবেন।<En className="text-sm text-muted">Check the papers and the ground before buying land: what matched, what did not, what to do next.</En></p>
            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-1 text-sm leading-6"><h3 className="font-semibold">সমস্যা<En className="text-muted">Problem</En></h3><p>অংশের চেয়ে বেশি বিক্রি, ভুল দাগ, নামজারিতে ওয়ারিশ বাদ; কাগজে চাষের জমি অথচ মাঠে পানি বা নদীভাঙন। সাধারণ ক্রেতা এগুলো নিজে মেলাতে পারেন না।</p></div>
              <div className="space-y-1 text-sm leading-6"><h3 className="font-semibold">সমাধান<En className="text-muted">Solution</En></h3><p>নথি পড়ে ১৩টি নিয়মে মেলানো, ২০১৯–২০২৫ সালের স্যাটেলাইট ছবিতে আশেপাশের পানি ও গাছের প্রবণতা, উৎসসহ ফলাফল ও পরের কাজের তালিকা।</p></div>
              <div className="space-y-1 text-sm leading-6"><h3 className="font-semibold">কার জন্য<En className="text-muted">Who it is for</En></h3><p>জমির ক্রেতা; বিদেশে থাকা প্রবাসী মালিক (খতিয়ান নজরদারি); ব্যাংক ও এসক্রো অংশীদার।</p></div>
              <div className="space-y-1 text-sm leading-6"><h3 className="font-semibold">কেন এখন<En className="text-muted">Why now</En></h3><p>জলবায়ুর ঝুঁকি: নদীভাঙন ও জলাবদ্ধতা জমির দাম ও ব্যবহার বদলায়, অথচ কাগজে তা ধরা পড়ে না।</p></div>
            </div>
            <p className="rounded-[var(--radius-control)] border border-dashed border-gold/50 bg-warn-bg/40 p-3 text-sm leading-6"><b>ব্যবসার ভাবনা (পরিকল্পনা, এখনো চালু নয়):</b> প্রতি রিপোর্টে ফি; ব্যাংক ও এসক্রো অংশীদারিত্ব।<En className="text-muted">Business model ideas (plans, not live): per-report fee; bank and escrow partners.</En></p>
          </Section>

          <Section id="tour" bn="প্রোডাক্ট ট্যুর" en="Product tour">
            <ul className="grid gap-4 sm:grid-cols-2">
              {SHOTS.map(([f, bn, en]) => (
                <li key={f}><figure className="overflow-hidden rounded-[var(--radius-control)] border border-edge bg-bg shadow-rest">
                  <Image src={`/docs/${f}.png`} alt={bn} width={1440} height={810} className="h-auto w-full" />
                  <figcaption className="p-3 text-sm text-ink">{bn}<En className="text-muted">{en}</En></figcaption>
                </figure></li>
              ))}
            </ul>
          </Section>

          <Section id="architecture" bn="আর্কিটেকচার" en="Architecture">
            <div aria-label="Next.js থেকে FastAPI, তারপর ডেটাবেস, ফাইল, সারি, ওয়ার্কার ও Sentinel সার্ভিস" role="img" className="grid gap-2 text-center text-sm font-semibold">
              <div className="mx-auto w-full max-w-xs rounded-[var(--radius-control)] border border-accent/30 bg-accent-soft px-3 py-2">Next.js</div>
              <span aria-hidden="true" className="text-accent">↓ /api</span>
              <div className="mx-auto w-full max-w-xs rounded-[var(--radius-control)] border border-accent/30 bg-accent-soft px-3 py-2">FastAPI</div>
              <span aria-hidden="true" className="text-accent">↓</span>
              <div className="grid grid-cols-3 gap-2">{["PostgreSQL", "MinIO", "Redis"].map((n) => <div key={n} className="rounded-[var(--radius-control)] border border-edge bg-surface px-2 py-2 shadow-rest">{n}</div>)}</div>
              <span aria-hidden="true" className="text-accent">↓ Redis</span>
              <div className="grid grid-cols-2 gap-2"><div className="rounded-[var(--radius-control)] border border-edge bg-surface px-2 py-2 shadow-rest">Celery: নথি</div><div className="rounded-[var(--radius-control)] border border-sat/30 bg-sat-soft px-2 py-2">Celery: স্যাটেলাইট</div></div>
              <span aria-hidden="true" className="text-right text-sat sm:pr-[22%]">↓</span>
              <div className="ml-auto w-full max-w-sm rounded-[var(--radius-control)] border border-sat/30 bg-sat-soft px-3 py-2">Sentinel সার্ভিস: U-Net + Earth Engine</div>
            </div>
            <dl className="grid gap-2 sm:grid-cols-2">
              {ARCH.map(([n, bn, en]) => <div key={n} className="rounded-[var(--radius-control)] bg-bg/60 p-3 text-sm"><dt className="font-semibold">{n}</dt><dd>{bn}<En className="text-muted">{en}</En></dd></div>)}
            </dl>
          </Section>

          <Section id="ai" bn="AI ও ডেটা" en="AI & data">
            <h3 className="font-semibold text-ink">নথি পড়া<En className="text-muted">Extraction</En></h3>
            <ul className="list-disc space-y-1 pl-5 text-sm leading-6">
              <li>OCR (Tesseract) বা vision LLM নথির ছাপা লেখা পড়ে; প্রম্পটের নিয়ম: যেমন ছাপা তেমন কপি, অনুমান বা হিসাব নয়, একক বদল নয়।<En className="text-muted">Prompt rules: copy exactly as printed, never guess or compute, never convert units.</En></li>
              <li>NID, ফোন বা জন্মনিবন্ধন নম্বর কখনো ফেরত দেওয়া হয় না; এর কোনো ঘরই নেই।<En className="text-muted">NID, phone and birth-registration numbers are never returned.</En></li>
              <li>তারপর normalize: বাংলা অঙ্ক, শতাংশে একক, নাম; শেষে ১৩টি নিয়ম।<En className="text-muted">Then normalisation, then 13 document rules.</En></li>
            </ul>
            <h3 className="font-semibold text-ink">স্যাটেলাইট মডেল (যাচাই সেটে)<En className="text-muted">Satellite models (validation)</En></h3>
            <div className="grid gap-2 sm:grid-cols-3 lg:grid-cols-4">
              <Stat v="0.824" bn="U-Net: পানির IoU" en="U-Net water IoU" />
              <Stat v="0.690" bn="U-Net: গাছের IoU" en="U-Net tree IoU" />
              <Stat v="0.739" bn="U-Net: পিক্সেল নির্ভুলতা" en="U-Net pixel accuracy" />
              <Stat v="0.404" bn="U-Net: mIoU (১০ শ্রেণী)" en="U-Net mean IoU (10 classes)" />
              <Stat v="0.937" bn="গাছে ঢাকা %: R²" en="Tree cover %: R² (5-fold CV)" />
              <Stat v="5.43" bn="গাছে ঢাকা %: MAE (শতাংশ-বিন্দু)" en="Tree cover %: MAE (points)" />
              <Stat v="0.72" bn="গাছের সংখ্যা/হেক্টর: R²" en="Trees per ha: R² (5-fold CV)" />
              <Stat v="50" bn="লেবেল করা এলাকা (৪০ প্রশিক্ষণ, ১০ যাচাই)" en="Labelled areas (40 train, 10 val)" />
              <Stat v="300" bn="গাছ গোনা বর্গ" en="Counted squares" />
            </div>
            <p className="text-sm leading-6 text-muted">দুর্বল দিক সৎভাবে: খালি মাটি, রাস্তা ও ঝোপের IoU প্রায় ০; তাই অ্যাপ শুধু পানি, সবুজ ও গাছের প্রবণতা ব্যবহার করে।<En>Bare soil, road and shrub IoU are near 0, so the app uses only water, green and tree trends.</En></p>
            <h3 className="font-semibold text-ink">প্রবণতা<En className="text-muted">Trend statistics</En></h3>
            <p className="text-sm leading-6">Theil-Sen ঢাল; ৩×MAD-এর বাইরের বছর outlier (পানির ক্ষেত্রে শুধু নিচের দিকে, কারণ বেশি পানি সত্যিকারের বন্যা হতে পারে); কম পরিষ্কার ছবির বছর low-confidence; স্থায়ী বদলে অন্তত ৪টি পরিষ্কার বছর লাগে।<En className="text-muted">Theil-Sen slope; 3×MAD outliers (water: low side only); low-confidence years; 4 clean years for a lasting change.</En></p>
            <h3 className="font-semibold text-ink">পরীক্ষা (২০২৬-১১-২০ চালানো)<En className="text-muted">Evaluation: test runs on 2026-11-20</En></h3>
            <div className="grid gap-2 sm:grid-cols-4">
              <Stat v="725" bn="ব্যাকএন্ড টেস্ট" en="Backend tests (pytest)" />
              <Stat v="148" bn="ML ডেটা টেস্ট" en="ML tests (pytest)" />
              <Stat v="12" bn="Sentinel টেস্ট" en="Sentinel tests" />
              <Stat v="5" bn="ফ্রন্টএন্ড ইউনিট টেস্ট" en="Frontend unit tests" />
            </div>
            <h3 className="font-semibold text-ink">ডেটার উৎস<En className="text-muted">Data provenance</En></h3>
            <p className="text-sm leading-6">নথি: সম্পূর্ণ কৃত্রিম (ml/synth), ডেটাসেট v1-এ ৫০টি কেস, ১৫০টি পরিষ্কার ছবি ও ৩০০টি ফোন-ছবির মতো কপি; প্রতিটি ফাইলের sha256 রাখা। স্যাটেলাইট: Copernicus Sentinel-1/2, Google Earth Engine দিয়ে।<En className="text-muted">Documents are fully synthetic (dataset v1: 50 cases, 150 clean images, 300 augmented copies, sha256 per file). Satellite: Copernicus Sentinel-1/2 via Earth Engine.</En></p>
          </Section>

          <Section id="privacy" bn="গোপনীয়তা ও দায়িত্বশীল AI" en="Privacy & responsible AI">
            <ul className="space-y-2 text-sm leading-6">
              <li>কখনো রাখা হয় না: NID নম্বর বা ছবি, সেলফি, মুখের তথ্য, স্বাক্ষর, ফোন নম্বর, জন্মনিবন্ধন নম্বর। পরিচয় যাচাইয়ের শুধু ফলাফল রাখা হয়।<En className="text-muted">Never stored: NID numbers/images, selfies, face data, signatures, phone or birth-registration numbers.</En></li>
              <li>LLM-এ (Gemini ফ্রি টিয়ার) শুধু কৃত্রিম নথি পাঠানো হয়, কারণ সেখানে ইনপুট মডেল উন্নয়নে ব্যবহার হতে পারে।<En className="text-muted">Only synthetic documents go to the Gemini free tier.</En></li>
              {limits.map(([b, e]) => <li key={e}>{b}<En className="text-muted">{e}</En></li>)}
            </ul>
          </Section>

          <Section id="roadmap" bn="অবস্থা ও পরিকল্পনা" en="Status & roadmap">
            <div className="grid gap-3 md:grid-cols-2">
              <div><h3 className="font-semibold text-ok">আজ কাজ করে<En className="text-muted">Works today</En></h3>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6"><li>নথি পড়া, ১৩টি নিয়ম, উৎসসহ ফলাফল, PDF রিপোর্ট</li><li>মালিকানার সময়রেখা</li><li>স্যাটেলাইট যাচাই (২০১৯–২০২৫, ফেব্রুয়ারি)</li><li>বায়না এসক্রো ও পরিচয় যাচাই (নমুনা ব্যাংক ও প্রোভাইডার)</li><li>প্রবাসী গার্ডিয়ান: খতিয়ানের কপি মিলিয়ে বদল জানানো</li></ul></div>
              <div><h3 className="font-semibold text-accent">পরিকল্পনা<En className="text-muted">Planned</En></h3>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6"><li>Oracle Cloud-এ স্থায়ী ডিপ্লয়মেন্ট</li><li>বর্ষার রাডার দিয়ে বন্যা যাচাই</li><li>ভাষা বদলের বোতাম</li><li>গার্ডিয়ানে মাসিক স্যাটেলাইট সতর্কতা</li></ul></div>
            </div>
          </Section>

          <Section id="team" bn="টিম ও লিংক" en="Team & links">
            <p className="text-sm">টিম <b>2:29 AM Error</b><En className="text-muted">Team 2:29 AM Error</En></p>
            <ul className="flex flex-wrap gap-2 text-sm">
              <li><a href="https://github.com/sourav7-1/JomIGuard" target="_blank" rel="noopener noreferrer" className="inline-flex min-h-11 flex-col justify-center rounded-[var(--radius-control)] border border-line bg-surface px-3 font-semibold text-accent">GitHub রিপো ↗<En>GitHub repo</En></a></li>
              <li><a href="https://github.com/sourav7-1/JomIGuard/releases/tag/model-v1" target="_blank" rel="noopener noreferrer" className="inline-flex min-h-11 flex-col justify-center rounded-[var(--radius-control)] border border-line bg-surface px-3 font-semibold text-accent">মডেল রিলিজ ↗<En>Model release (model-v1)</En></a></li>
              <li><span className="inline-flex min-h-11 flex-col justify-center rounded-[var(--radius-control)] border border-dashed border-line px-3 text-muted">ডেমো ভিডিও: শিগগির<En>Demo video: coming soon</En></span></li>
            </ul>
          </Section>

          <Section id="status" bn="লাইভ অবস্থা" en="Live status">
            <DocsStatus />
          </Section>
        </div>
      </div>
    </div>
  );
}
