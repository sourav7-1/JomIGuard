"use client";

import Link from "next/link";
import { bnDigits } from "@/lib/digits";
import { useLang, useStrings } from "@/lib/lang";

const steps = [
  { title: "চুক্তির শর্ত ঠিক করুন", titleEn: "Set the contract conditions", detail: "বায়না কোন শর্তে ছাড় হবে বা ফেরত যাবে তা চুক্তিতে নির্ধারিত থাকে।", detailEn: "The contract sets when the bayna is released and when it is refunded." },
  { title: "ব্যাংক অংশীদার অর্থ রাখে", titleEn: "A partner bank holds the money", detail: "বায়নার টাকা অংশীদার ব্যাংকের কাছে থাকে; JomiGuard টাকা ধরে না।", detailEn: "The bayna money stays with the partner bank; JomiGuard never holds money." },
  { title: "শর্ত অনুযায়ী নিষ্পত্তি", titleEn: "Settled by the conditions", detail: "চুক্তির শর্ত পূরণ হলে অর্থ ছাড় হয়, অন্যথায় ফেরতের ব্যবস্থা হয়।", detailEn: "If the conditions are met the money is released; otherwise it is refunded." },
];

export default function EscrowPage() {
  const strings = useStrings();
  const en = useLang() === "en";
  const t = (b: string, e: string) => (en ? e : b);
  return (
    <div className="mx-auto max-w-5xl space-y-10 py-2 sm:space-y-12">
      <header className="max-w-2xl border-b border-line pb-7">
        <p className="mb-3 flex items-center gap-3 text-sm font-semibold text-accent"><span className="h-px w-8 bg-gold" />{t("লেনদেনের সময়", "During the deal")}</p>
        <h1 className="text-3xl font-semibold leading-tight tracking-tight text-ink sm:text-4xl">{strings.pages.escrow.title}</h1>
        <p className="mt-3 text-base leading-7 text-muted">{strings.pages.escrow.desc}</p>
      </header>

      <section aria-label={t("বায়না Escrow-এর ধাপ", "Bayna escrow steps")} className="grid divide-y divide-line border-y border-line md:grid-cols-3 md:divide-x md:divide-y-0">
        {steps.map((step, index) => (
          <article key={step.title} className="py-6 md:px-6 md:first:pl-0 md:last:pr-0">
            <p className="font-mono text-sm text-gold">{en ? `0${index + 1}` : bnDigits(`0${index + 1}`)}</p>
            <h2 className="mt-4 text-xl font-semibold text-ink">{en ? step.titleEn : step.title}</h2>
            <p className="mt-2 text-sm leading-7 text-muted">{en ? step.detailEn : step.detail}</p>
          </article>
        ))}
      </section>

      <p className="max-w-3xl border-l-2 border-gold pl-4 text-sm leading-7 text-muted">{strings.pages.escrow.note}</p>
      <Link href="/upload" className="inline-flex min-h-11 items-center text-sm font-semibold text-accent underline decoration-gold decoration-2 underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">{t("জমির কাগজ যাচাই করুন", "Check the land papers")}</Link>
    </div>
  );
}
