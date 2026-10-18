import Link from "next/link";
import { strings } from "@/lib/strings";

const steps = [
  { title: "চুক্তির শর্ত ঠিক করুন", detail: "বায়না কোন শর্তে ছাড় হবে বা ফেরত যাবে তা চুক্তিতে নির্ধারিত থাকে।" },
  { title: "ব্যাংক অংশীদার অর্থ রাখে", detail: "বায়নার টাকা অংশীদার ব্যাংকের কাছে থাকে; JomiGuard টাকা ধরে না।" },
  { title: "শর্ত অনুযায়ী নিষ্পত্তি", detail: "চুক্তির শর্ত পূরণ হলে অর্থ ছাড় হয়, অন্যথায় ফেরতের ব্যবস্থা হয়।" },
];

export default function EscrowPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-10 py-2 sm:space-y-12">
      <header className="max-w-2xl border-b border-line pb-7">
        <p className="mb-3 flex items-center gap-3 text-sm font-semibold text-accent"><span className="h-px w-8 bg-gold" />লেনদেনের সময়</p>
        <h1 className="text-3xl font-semibold leading-tight tracking-tight text-ink sm:text-4xl">{strings.pages.escrow.title}</h1>
        <p className="mt-3 text-base leading-7 text-muted">{strings.pages.escrow.desc}</p>
      </header>

      <section aria-label="বায়না Escrow-এর ধাপ" className="grid divide-y divide-line border-y border-line md:grid-cols-3 md:divide-x md:divide-y-0">
        {steps.map((step, index) => (
          <article key={step.title} className="py-6 md:px-6 md:first:pl-0 md:last:pr-0">
            <p className="font-mono text-sm text-gold">০{index + 1}</p>
            <h2 className="mt-4 text-xl font-semibold text-ink">{step.title}</h2>
            <p className="mt-2 text-sm leading-7 text-muted">{step.detail}</p>
          </article>
        ))}
      </section>

      <p className="max-w-3xl border-l-2 border-gold pl-4 text-sm leading-7 text-muted">{strings.pages.escrow.note}</p>
      <Link href="/upload" className="inline-flex min-h-11 items-center text-sm font-semibold text-accent underline decoration-gold decoration-2 underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">জমির কাগজ যাচাই করুন</Link>
    </div>
  );
}
