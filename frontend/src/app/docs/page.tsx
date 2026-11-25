import type { Metadata } from "next";
import Image from "next/image";
import { Card } from "@/components/ui/Card";
import { T } from "@/lib/lang";
import { DocsStatus } from "@/components/DocsStatus";
import { limits } from "@/lib/explain";

export const metadata: Metadata = { title: "ডকস · Docs · JomiGuard Sentinel" };

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
      <h2 id={id} className="font-heading text-2xl font-bold text-ink sm:text-3xl"><T bn={bn} en={en} /></h2>
      {children}
    </Card>
  );
}

const Stat = ({ v, bn, en }: { v: string; bn: string; en: string }) => (
  <div className="rounded-[var(--radius-control)] border border-edge bg-bg/60 p-3"><p className="font-mono text-2xl font-bold text-accent">{v}</p><p className="text-sm text-ink"><T bn={bn} en={en} /></p></div>
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
        <p className="text-sm font-semibold text-accent"><T bn={"পিচ ও টেকনিক্যাল হোয়াইটপেপার"} en={"Live pitch + technical whitepaper"} /></p>
        <h1 className="font-heading text-4xl font-bold text-ink sm:text-5xl"><T bn={"ডকস"} en={"Docs"} /></h1>
      </header>
      <div className="lg:grid lg:grid-cols-[14rem_1fr] lg:gap-8">
        <nav aria-label="Table of contents" className="sticky top-[6.1rem] z-20 -mx-4 mb-4 overflow-x-auto [scrollbar-width:none] border-y border-edge bg-bg/90 px-4 py-2 backdrop-blur lg:top-40 lg:mx-0 lg:mb-0 lg:self-start lg:overflow-visible lg:rounded-[var(--radius-card)] lg:border lg:bg-surface lg:p-3 lg:shadow-rest">
          <ol className="flex gap-2 lg:flex-col lg:gap-0.5">
            {TOC.map(([id, bn, en]) => (
              <li key={id} className="shrink-0"><a href={`#${id}`} className="block min-h-11 rounded-[var(--radius-control)] px-3 py-1.5 text-sm font-semibold text-ink hover:bg-accent-soft"><T bn={bn} en={en} /></a></li>
            ))}
          </ol>
        </nav>

        <div className="min-w-0 space-y-6">
          <Section id="pitch" bn="পিচ" en="Pitch">
            <p className="text-lg font-semibold leading-8 text-ink"><T bn={"জমি কেনার আগে কাগজ আর মাটি, দুটোই যাচাই: কী মিলেছে, কী মেলেনি, এরপর কী করবেন।"} en={"Check the papers and the ground before buying land: what matched, what did not, what to do next."} /></p>
            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-1 text-sm leading-6"><h3 className="font-semibold"><T bn={"সমস্যা"} en={"Problem"} /></h3><p><T bn={"অংশের চেয়ে বেশি বিক্রি, ভুল দাগ, নামজারিতে ওয়ারিশ বাদ; কাগজে চাষের জমি অথচ মাঠে পানি বা নদীভাঙন। সাধারণ ক্রেতা এগুলো নিজে মেলাতে পারেন না।"} en={"Selling more than one's share, wrong dag numbers, heirs left out of the mutation; cropland on paper but water or river erosion on the ground. Ordinary buyers cannot check these themselves."} /></p></div>
              <div className="space-y-1 text-sm leading-6"><h3 className="font-semibold"><T bn={"সমাধান"} en={"Solution"} /></h3><p><T bn={"নথি পড়ে ১৩টি নিয়মে মেলানো, ২০১৯–২০২৫ সালের স্যাটেলাইট ছবিতে আশেপাশের পানি ও গাছের প্রবণতা, উৎসসহ ফলাফল ও পরের কাজের তালিকা।"} en={"Read the documents and compare them with 13 rules, show water and tree trends nearby in 2019–2025 satellite images, and give findings with sources plus a list of next tasks."} /></p></div>
              <div className="space-y-1 text-sm leading-6"><h3 className="font-semibold"><T bn={"কার জন্য"} en={"Who it is for"} /></h3><p><T bn={"জমির ক্রেতা; বিদেশে থাকা প্রবাসী মালিক (খতিয়ান নজরদারি); ব্যাংক ও এসক্রো অংশীদার।"} en={"Land buyers; probashi owners living abroad (khatian watch); bank and escrow partners."} /></p></div>
              <div className="space-y-1 text-sm leading-6"><h3 className="font-semibold"><T bn={"কেন এখন"} en={"Why now"} /></h3><p><T bn={"জলবায়ুর ঝুঁকি: নদীভাঙন ও জলাবদ্ধতা জমির দাম ও ব্যবহার বদলায়, অথচ কাগজে তা ধরা পড়ে না।"} en={"Climate risk: river erosion and waterlogging change land value and use, yet the papers do not show it."} /></p></div>
            </div>
            <p className="rounded-[var(--radius-control)] border border-dashed border-gold/50 bg-warn-bg/40 p-3 text-sm leading-6"><T bn={<><b>ব্যবসার ভাবনা (পরিকল্পনা, এখনো চালু নয়):</b> প্রতি রিপোর্টে ফি; ব্যাংক ও এসক্রো অংশীদারিত্ব।</>} en={<><b>Business model ideas (plans, not live):</b> per-report fee; bank and escrow partners.</>} /></p>
          </Section>

          <Section id="tour" bn="প্রোডাক্ট ট্যুর" en="Product tour">
            <ul className="grid gap-4 sm:grid-cols-2">
              {SHOTS.map(([f, bn, en]) => (
                <li key={f}><figure className="overflow-hidden rounded-[var(--radius-control)] border border-edge bg-bg shadow-rest">
                  <Image src={`/docs/${f}.png`} alt={bn} width={1440} height={810} className="h-auto w-full" />
                  <figcaption className="p-3 text-sm text-ink"><T bn={bn} en={en} /></figcaption>
                </figure></li>
              ))}
            </ul>
          </Section>

          <Section id="architecture" bn="আর্কিটেকচার" en="Architecture">
            <div aria-label="Next.js to FastAPI, then database, files, queues, workers and the Sentinel service" role="img" className="grid gap-2 text-center text-sm font-semibold">
              <div className="mx-auto w-full max-w-xs rounded-[var(--radius-control)] border border-accent/30 bg-accent-soft px-3 py-2">Next.js</div>
              <span aria-hidden="true" className="text-accent">↓ /api</span>
              <div className="mx-auto w-full max-w-xs rounded-[var(--radius-control)] border border-accent/30 bg-accent-soft px-3 py-2">FastAPI</div>
              <span aria-hidden="true" className="text-accent">↓</span>
              <div className="grid grid-cols-3 gap-2">{["PostgreSQL", "MinIO", "Redis"].map((n) => <div key={n} className="rounded-[var(--radius-control)] border border-edge bg-surface px-2 py-2 shadow-rest">{n}</div>)}</div>
              <span aria-hidden="true" className="text-accent">↓ Redis</span>
              <div className="grid grid-cols-2 gap-2"><div className="rounded-[var(--radius-control)] border border-edge bg-surface px-2 py-2 shadow-rest"><T bn="Celery: নথি" en="Celery: documents" /></div><div className="rounded-[var(--radius-control)] border border-sat/30 bg-sat-soft px-2 py-2"><T bn="Celery: স্যাটেলাইট" en="Celery: satellite" /></div></div>
              <span aria-hidden="true" className="text-right text-sat sm:pr-[22%]">↓</span>
              <div className="ml-auto w-full max-w-sm rounded-[var(--radius-control)] border border-sat/30 bg-sat-soft px-3 py-2"><T bn="Sentinel সার্ভিস" en="Sentinel service" />: U-Net + Earth Engine</div>
            </div>
            <dl className="grid gap-2 sm:grid-cols-2">
              {ARCH.map(([n, bn, en]) => <div key={n} className="rounded-[var(--radius-control)] bg-bg/60 p-3 text-sm"><dt className="font-semibold">{n}</dt><dd><T bn={bn} en={en} /></dd></div>)}
            </dl>
          </Section>

          <Section id="ai" bn="AI ও ডেটা" en="AI & data">
            <h3 className="font-semibold text-ink"><T bn={"নথি পড়া"} en={"Extraction"} /></h3>
            <ul className="list-disc space-y-1 pl-5 text-sm leading-6">
              <li><T bn={"OCR (Tesseract) বা vision LLM নথির ছাপা লেখা পড়ে; প্রম্পটের নিয়ম: যেমন ছাপা তেমন কপি, অনুমান বা হিসাব নয়, একক বদল নয়।"} en={"Prompt rules: copy exactly as printed, never guess or compute, never convert units."} /></li>
              <li><T bn={"NID, ফোন বা জন্মনিবন্ধন নম্বর কখনো ফেরত দেওয়া হয় না; এর কোনো ঘরই নেই।"} en={"NID, phone and birth-registration numbers are never returned."} /></li>
              <li><T bn={"তারপর normalize: বাংলা অঙ্ক, শতাংশে একক, নাম; শেষে ১৩টি নিয়ম।"} en={"Then normalisation, then 13 document rules."} /></li>
            </ul>
            <h3 className="font-semibold text-ink"><T bn={"স্যাটেলাইট মডেল (যাচাই সেটে)"} en={"Satellite models (validation)"} /></h3>
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
            <p className="text-sm leading-6 text-muted"><T bn={"দুর্বল দিক সৎভাবে: খালি মাটি, রাস্তা ও ঝোপের IoU প্রায় ০; তাই অ্যাপ শুধু পানি, সবুজ ও গাছের প্রবণতা ব্যবহার করে।"} en={"Bare soil, road and shrub IoU are near 0, so the app uses only water, green and tree trends."} /></p>
            <h3 className="font-semibold text-ink"><T bn={"প্রবণতা"} en={"Trend statistics"} /></h3>
            <p className="text-sm leading-6"><T bn={"Theil-Sen ঢাল; ৩×MAD-এর বাইরের বছর outlier (পানির ক্ষেত্রে শুধু নিচের দিকে, কারণ বেশি পানি সত্যিকারের বন্যা হতে পারে); কম পরিষ্কার ছবির বছর low-confidence; স্থায়ী বদলে অন্তত ৪টি পরিষ্কার বছর লাগে।"} en={"Theil-Sen slope; 3×MAD outliers (water: low side only); low-confidence years; 4 clean years for a lasting change."} /></p>
            <h3 className="font-semibold text-ink"><T bn={"পরীক্ষা (২০২৬-১১-২০ চালানো)"} en={"Evaluation: test runs on 2026-11-20"} /></h3>
            <div className="grid gap-2 sm:grid-cols-4">
              <Stat v="725" bn="ব্যাকএন্ড টেস্ট" en="Backend tests (pytest)" />
              <Stat v="148" bn="ML ডেটা টেস্ট" en="ML tests (pytest)" />
              <Stat v="12" bn="Sentinel টেস্ট" en="Sentinel tests" />
              <Stat v="5" bn="ফ্রন্টএন্ড ইউনিট টেস্ট" en="Frontend unit tests" />
            </div>
            <h3 className="font-semibold text-ink"><T bn={"ডেটার উৎস"} en={"Data provenance"} /></h3>
            <p className="text-sm leading-6"><T bn={"নথি: সম্পূর্ণ কৃত্রিম (ml/synth), ডেটাসেট v1-এ ৫০টি কেস, ১৫০টি পরিষ্কার ছবি ও ৩০০টি ফোন-ছবির মতো কপি; প্রতিটি ফাইলের sha256 রাখা। স্যাটেলাইট: Copernicus Sentinel-1/2, Google Earth Engine দিয়ে।"} en={"Documents are fully synthetic (dataset v1: 50 cases, 150 clean images, 300 augmented copies, sha256 per file). Satellite: Copernicus Sentinel-1/2 via Earth Engine."} /></p>
          </Section>

          <Section id="privacy" bn="গোপনীয়তা ও দায়িত্বশীল AI" en="Privacy & responsible AI">
            <ul className="space-y-2 text-sm leading-6">
              <li><T bn={"কখনো রাখা হয় না: NID নম্বর বা ছবি, সেলফি, মুখের তথ্য, স্বাক্ষর, ফোন নম্বর, জন্মনিবন্ধন নম্বর। পরিচয় যাচাইয়ের শুধু ফলাফল রাখা হয়।"} en={"Never stored: NID numbers/images, selfies, face data, signatures, phone or birth-registration numbers."} /></li>
              <li><T bn={"LLM-এ (Gemini ফ্রি টিয়ার) শুধু কৃত্রিম নথি পাঠানো হয়, কারণ সেখানে ইনপুট মডেল উন্নয়নে ব্যবহার হতে পারে।"} en={"Only synthetic documents go to the Gemini free tier."} /></li>
              {limits.map(([b, e]) => <li key={e}><T bn={b} en={e} /></li>)}
            </ul>
          </Section>

          <Section id="roadmap" bn="অবস্থা ও পরিকল্পনা" en="Status & roadmap">
            <div className="grid gap-3 md:grid-cols-2">
              <div><h3 className="font-semibold text-ok"><T bn={"আজ কাজ করে"} en={"Works today"} /></h3>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6"><li><T bn={"নথি পড়া, ১৩টি নিয়ম, উৎসসহ ফলাফল, PDF রিপোর্ট"} en={"Document reading, 13 rules, findings with sources, PDF report"} /></li><li><T bn={"মালিকানার সময়রেখা"} en={"Ownership timeline"} /></li><li><T bn={"স্যাটেলাইট যাচাই (২০১৯–২০২৫, ফেব্রুয়ারি)"} en={"Satellite check (2019–2025, February)"} /></li><li><T bn={"বায়না এসক্রো ও পরিচয় যাচাই (নমুনা ব্যাংক ও প্রোভাইডার)"} en={"Bayna escrow and identity check (sample bank and provider)"} /></li><li><T bn={"প্রবাসী গার্ডিয়ান: খতিয়ানের কপি মিলিয়ে বদল জানানো"} en={"Probashi guardian: compares khatian copies and reports changes"} /></li></ul></div>
              <div><h3 className="font-semibold text-accent"><T bn={"পরিকল্পনা"} en={"Planned"} /></h3>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6"><li><T bn={"Oracle Cloud-এ স্থায়ী ডিপ্লয়মেন্ট"} en={"Permanent deployment on Oracle Cloud"} /></li><li><T bn={"বর্ষার রাডার দিয়ে বন্যা যাচাই"} en={"Flood check with monsoon radar"} /></li><li><T bn={"গার্ডিয়ানে মাসিক স্যাটেলাইট সতর্কতা"} en={"Monthly satellite alerts in the guardian"} /></li></ul></div>
            </div>
          </Section>

          <Section id="team" bn="টিম ও লিংক" en="Team & links">
            <p className="text-sm"><T bn="টিম" en="Team" /> <b>2:29 AM Error</b></p>
            <ul className="flex flex-wrap gap-2 text-sm">
              <li><a href="https://github.com/sourav7-1/JomIGuard" target="_blank" rel="noopener noreferrer" className="inline-flex min-h-11 flex-col justify-center rounded-[var(--radius-control)] border border-line bg-surface px-3 font-semibold text-accent"><T bn={"GitHub রিপো ↗"} en={"GitHub repo"} /></a></li>
              <li><a href="https://github.com/sourav7-1/JomIGuard/releases/tag/model-v1" target="_blank" rel="noopener noreferrer" className="inline-flex min-h-11 flex-col justify-center rounded-[var(--radius-control)] border border-line bg-surface px-3 font-semibold text-accent"><T bn={"মডেল রিলিজ ↗"} en={"Model release (model-v1)"} /></a></li>
              <li><span className="inline-flex min-h-11 flex-col justify-center rounded-[var(--radius-control)] border border-dashed border-line px-3 text-muted"><T bn={"ডেমো ভিডিও: শিগগির"} en={"Demo video: coming soon"} /></span></li>
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
