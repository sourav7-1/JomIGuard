import Link from "next/link";
import { strings } from "@/lib/strings";
import { officialLinks, services } from "@/lib/services";
import { ServiceIcon } from "@/components/ServiceIcon";

// Every answer repeats what the app already says elsewhere (disclaimer, satellite note,
// identity rules, README); nothing here is new legal or service advice.
const faq = [
  { q: "JomiGuard Sentinel কি সরকারি সেবা?", a: `না। ${strings.app.independentNote} সার্টিফাইড খতিয়ান, নামজারি বা ভূমি উন্নয়ন কর সরকারি সাইট থেকে নিতে হয়; নিচে সেই সাইটগুলোর link আছে।` },
  { q: "‘কম ঝুঁকি’ দেখালে কি জমি কেনা যায়?", a: `এই ব্যবস্থা জমি নিয়ে কোনো নিশ্চয়তা দেয় না। ${strings.app.disclaimer}` },
  { q: "স্যাটেলাইট ফল কেন প্লটের চারপাশের প্রায় ২০০ মিটার এলাকার?", a: "ছবির প্রতিটি বিন্দু ১০ মিটার, তাই ফলাফল প্লটের চারপাশের প্রায় ২০০ মিটার এলাকার, প্লটের সীমানার ভেতরের নয়। স্যাটেলাইট যাচাই কাগজের পরীক্ষার ঝুঁকির মাত্রা বদলায় না; মাঠে গিয়ে নিজে মিলিয়ে দেখুন।" },
  { q: "বিক্রেতার পরিচয় যাচাইয়ে কী রাখা হয়?", a: "শুধু যাচাইয়ের ফল রাখা হয়। NID নম্বর, NID-এর ছবি, সেলফি, ফোন নম্বর বা স্বাক্ষর রাখা হয় না।" },
  { q: "এই ডেমোতে কোন তথ্য আছে?", a: `${strings.pages.home.samplePill}। ডেমোতে আসল দলিল বা আসল পরিচয়ের তথ্য upload করবেন না।` },
  { q: "যাচাইয়ের পরে কী করব?", a: "কেসের পাতার “এখন কী করবেন” অংশে অমিল আর স্যাটেলাইট ফল থেকে পাওয়া পরের কাজগুলো দেখা যায়। সেগুলো ধরে কাজ করুন এবং PDF রিপোর্ট সঙ্গে রাখুন।" },
];

export default function HelpPage() {
  return (
    <div className="mx-auto max-w-4xl space-y-10">
      <header className="space-y-2">
        <p className="flex items-center gap-3 text-sm font-semibold text-accent"><span className="h-px w-8 bg-gold" />সাহায্য</p>
        <h1 className="text-3xl font-semibold tracking-tight text-ink sm:text-4xl">কীভাবে ব্যবহার করবেন</h1>
        <p className="text-base leading-7 text-muted">প্রতিটি সেবার ধাপ আর সচরাচর জিজ্ঞাসার উত্তর।</p>
      </header>

      <section aria-labelledby="howto-title" className="space-y-3">
        <h2 id="howto-title" className="text-xl font-bold text-ink">সেবা অনুযায়ী ধাপ</h2>
        {services.map((s) => (
          <details key={s.id} id={s.id} className="group rounded-[var(--radius-card)] border border-line bg-surface shadow-[var(--shadow-card)] open:border-accent/40">
            <summary className="flex min-h-14 cursor-pointer list-none items-center gap-3 px-4 py-3 [&::-webkit-details-marker]:hidden">
              <span className={`inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${s.satellite ? "bg-sat-soft text-sat" : "bg-accent-soft text-accent"}`}><ServiceIcon path={s.icon} className="h-5 w-5" /></span>
              <span className="flex-1 font-semibold text-ink">{s.title}</span>
              <span aria-hidden="true" className="text-muted transition-transform group-open:rotate-180">▾</span>
            </summary>
            <div className="border-t border-line px-4 pb-4 pt-3">
              <ol className="list-decimal space-y-1.5 pl-5 text-sm leading-7 text-ink">
                {s.howTo.map((step) => <li key={step}>{step}</li>)}
              </ol>
              <Link href={s.start.href} className="mt-3 inline-flex min-h-11 items-center rounded-[var(--radius-control)] bg-accent px-4 text-sm font-semibold text-white">{s.title}: {s.start.label} →</Link>
            </div>
          </details>
        ))}
      </section>

      <section aria-labelledby="faq-title" className="space-y-3">
        <h2 id="faq-title" className="text-xl font-bold text-ink">সচরাচর জিজ্ঞাসা</h2>
        {faq.map((f) => (
          <details key={f.q} className="group rounded-[var(--radius-card)] border border-line bg-surface">
            <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 font-semibold text-ink [&::-webkit-details-marker]:hidden">
              {f.q}<span aria-hidden="true" className="text-muted transition-transform group-open:rotate-180">▾</span>
            </summary>
            <p className="border-t border-line px-4 pb-4 pt-3 text-sm leading-7 text-ink">{f.a}</p>
          </details>
        ))}
      </section>

      <section aria-labelledby="official-help-title" className="rounded-[var(--radius-card)] border border-dashed border-line bg-bg p-5">
        <h2 id="official-help-title" className="text-lg font-bold text-ink">সরকারি সেবার সাইট</h2>
        <ul className="mt-3 grid gap-3 sm:grid-cols-3">
          {officialLinks.map((l) => (
            <li key={l.href}>
              <a href={l.href} target="_blank" rel="noopener noreferrer" className="flex min-h-12 flex-col justify-center rounded-[var(--radius-control)] border border-line bg-surface px-4 py-2.5 hover:border-accent">
                <span className="text-sm font-semibold text-accent">{l.label} <span aria-hidden="true">↗</span></span>
                <span className="text-xs text-muted">সরকারি সাইট, আমাদের নয়</span>
              </a>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
