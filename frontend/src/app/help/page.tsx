"use client";

import Link from "next/link";
import { strings } from "@/lib/strings";
import { stringsEn } from "@/lib/strings-en";
import { officialLinks, services } from "@/lib/services";
import { ServiceIcon } from "@/components/ServiceIcon";
import { IconTile } from "@/components/ui/Card";
import { useLang } from "@/lib/lang";

// Every answer repeats what the app already says elsewhere (disclaimer, satellite note,
// identity rules, README); nothing here is new legal or service advice.
const faq = [
  { q: "JomiGuard Sentinel কি সরকারি সেবা?", a: `না। ${strings.app.independentNote} সার্টিফাইড খতিয়ান, নামজারি বা ভূমি উন্নয়ন কর সরকারি সাইট থেকে নিতে হয়; নিচে সেই সাইটগুলোর link আছে।`,
    qEn: "Is JomiGuard Sentinel a government service?", aEn: `No. ${stringsEn.app.independentNote} Certified khatian, mutation and land development tax come from government sites; links are below.` },
  { q: "‘কম ঝুঁকি’ দেখালে কি জমি কেনা যায়?", a: `এই ব্যবস্থা জমি নিয়ে কোনো নিশ্চয়তা দেয় না। ${strings.app.disclaimer}`,
    qEn: "If it shows ‘low risk’, can I buy the land?", aEn: `This service cannot vouch for the land. ${stringsEn.app.disclaimer}` },
  { q: "স্যাটেলাইট ফল কেন প্লটের চারপাশের প্রায় ২০০ মিটার এলাকার?", a: "ছবির প্রতিটি বিন্দু ১০ মিটার, তাই ফলাফল প্লটের চারপাশের প্রায় ২০০ মিটার এলাকার, প্লটের সীমানার ভেতরের নয়। স্যাটেলাইট যাচাই কাগজের পরীক্ষার ঝুঁকির মাত্রা বদলায় না; মাঠে গিয়ে নিজে মিলিয়ে দেখুন।",
    qEn: "Why do satellite results cover about 200 m around the plot?", aEn: "Each image pixel is 10 m, so results cover about 200 m around the plot, not only inside its boundary. The satellite check does not change the risk level from the papers; compare on the ground yourself." },
  { q: "বিক্রেতার পরিচয় যাচাইয়ে কী রাখা হয়?", a: "শুধু যাচাইয়ের ফল রাখা হয়। NID নম্বর, NID-এর ছবি, সেলফি, ফোন নম্বর বা স্বাক্ষর রাখা হয় না।",
    qEn: "What is kept from the seller identity check?", aEn: "Only the result. NID numbers, NID images, selfies, phone numbers and signatures are not kept." },
  { q: "এই ডেমোতে কোন তথ্য আছে?", a: `${strings.pages.home.samplePill}। ডেমোতে আসল দলিল বা আসল পরিচয়ের তথ্য upload করবেন না।`,
    qEn: "What data is in this demo?", aEn: `${stringsEn.pages.home.samplePill}. Do not upload real deeds or real identity data to the demo.` },
  { q: "যাচাইয়ের পরে কী করব?", a: "কেসের পাতার “এখন কী করবেন” অংশে অমিল আর স্যাটেলাইট ফল থেকে পাওয়া পরের কাজগুলো দেখা যায়। সেগুলো ধরে কাজ করুন এবং PDF রিপোর্ট সঙ্গে রাখুন।",
    qEn: "What do I do after the check?", aEn: "The “What to do now” part of the case page lists the next tasks from the mismatches and satellite results. Work through them and keep the PDF report with you." },
];

export default function HelpPage() {
  const en = useLang() === "en";
  const t = (b: string, e: string) => (en ? e : b);
  return (
    <div className="mx-auto max-w-4xl space-y-10">
      <header className="space-y-2">
        <p className="flex items-center gap-3 text-sm font-semibold text-accent"><span className="h-px w-8 bg-gold" />{t("সাহায্য", "Help")}</p>
        <h1 className="text-3xl font-semibold tracking-tight text-ink sm:text-4xl">{t("প্রশ্নোত্তর", "Questions and answers")}</h1>
        <p className="text-base leading-7 text-muted">{t("প্রতিটি সেবার ধাপ আর সচরাচর জিজ্ঞাসার উত্তর।", "Steps for every service and answers to common questions.")}</p>
      </header>

      <section aria-labelledby="howto-title" className="space-y-3">
        <h2 id="howto-title" className="text-xl font-bold text-ink">{t("সেবা অনুযায়ী ধাপ", "Steps by service")}</h2>
        {services.map((s) => (
          <details key={s.id} id={s.id} className="group surface-grad rounded-[var(--radius-card)] border border-edge bg-surface shadow-rest transition-shadow open:border-accent/40 open:shadow-raised">
            <summary className="flex min-h-14 cursor-pointer list-none items-center gap-3 px-4 py-3 [&::-webkit-details-marker]:hidden">
              <IconTile satellite={s.satellite} className="!h-10 !w-10"><ServiceIcon path={s.icon} className="h-5 w-5" /></IconTile>
              <span className="flex-1 font-semibold text-ink">{en ? s.titleEn : s.title}</span>
              <span aria-hidden="true" className="text-muted transition-transform group-open:rotate-180">▾</span>
            </summary>
            <div className="border-t border-line px-4 pb-4 pt-3">
              <ol className="list-decimal space-y-1.5 pl-5 text-sm leading-7 text-ink">
                {(en ? s.howToEn : s.howTo).map((step) => <li key={step}>{step}</li>)}
              </ol>
              <Link href={s.start.href} className="mt-3 inline-flex min-h-11 items-center rounded-[var(--radius-control)] bg-accent px-4 text-sm font-semibold text-white shadow-rest">{en ? s.titleEn : s.title}: {en ? s.start.labelEn : s.start.label} →</Link>
            </div>
          </details>
        ))}
      </section>

      <section aria-labelledby="faq-title" className="space-y-3">
        <h2 id="faq-title" className="text-xl font-bold text-ink">{t("সচরাচর জিজ্ঞাসা", "Common questions")}</h2>
        {faq.map((f) => (
          <details key={f.q} className="group surface-grad rounded-[var(--radius-card)] border border-edge bg-surface shadow-rest transition-shadow open:shadow-raised">
            <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 font-semibold text-ink [&::-webkit-details-marker]:hidden">
              {en ? f.qEn : f.q}<span aria-hidden="true" className="text-muted transition-transform group-open:rotate-180">▾</span>
            </summary>
            <p className="border-t border-line px-4 pb-4 pt-3 text-sm leading-7 text-ink">{en ? f.aEn : f.a}</p>
          </details>
        ))}
      </section>

      <section aria-labelledby="official-help-title" className="rounded-[var(--radius-card)] border border-dashed border-line bg-bg p-5">
        <h2 id="official-help-title" className="text-lg font-bold text-ink">{t("সরকারি সেবার সাইট", "Government service sites")}</h2>
        <ul className="mt-3 grid gap-3 sm:grid-cols-3">
          {officialLinks.map((l) => (
            <li key={l.href}>
              <a href={l.href} target="_blank" rel="noopener noreferrer" className="flex min-h-12 flex-col justify-center rounded-[var(--radius-control)] border border-line bg-surface px-4 py-2.5 hover:border-accent">
                <span className="text-sm font-semibold text-accent">{en ? l.labelEn : l.label} <span aria-hidden="true">↗</span></span>
                <span className="text-xs text-muted">{t("সরকারি সাইট, আমাদের নয়", "Government site, not ours")}</span>
              </a>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
