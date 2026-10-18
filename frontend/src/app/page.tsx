import Link from "next/link";
import { strings } from "@/lib/strings";

const services = [
  {
    title: "দলিলের তথ্য যাচাই",
    detail: "খতিয়ান, দলিল ও নামজারির তথ্য পাশাপাশি মিলিয়ে দেখুন।",
    href: "/upload",
    tag: "কেনার আগে",
  },
  {
    title: "মালিকানার ইতিহাস",
    detail: "নথিতে থাকা মালিকানা পরিবর্তনের ধারাবাহিকতা দেখুন।",
    href: "/cases/801bc1b6-b43c-5147-9b4f-b0baa3815cd0/timeline",
    tag: "কাগজপত্র থেকে",
  },
  {
    title: "বায়না Escrow",
    detail: "চুক্তির শর্তে বায়নার টাকা ব্যাংক অংশীদার পরিচালনা করে।",
    href: "/escrow",
    tag: "লেনদেনের সময়",
  },
  {
    title: "প্রবাসী Guardian",
    detail: "খতিয়ানের নতুন কপি আগেরটির সঙ্গে মিলিয়ে পরিবর্তন দেখুন।",
    href: "/guardian",
    tag: "কেনার পরে",
  },
];

const demoLinks = [
  { label: "demoCase1", href: "/cases/66c09208-d737-59f0-937e-de349f50899a" },
  { label: "demoCase26", href: "/cases/6c530a00-cc5c-5c6b-a341-ae4491761d4e" },
  { label: "demoDeedArchive26", href: "/cases/6c530a00-cc5c-5c6b-a341-ae4491761d4e#deed-archive-title" },
  { label: "demoCase29", href: "/cases/801bc1b6-b43c-5147-9b4f-b0baa3815cd0" },
  { label: "demoTimeline29", href: "/cases/801bc1b6-b43c-5147-9b4f-b0baa3815cd0/timeline" },
  { label: "demoGuardian", href: "/guardian" },
  { label: "demoEscrow26", href: "/escrow/demo-00026" },
] as const;

function ParcelStudy() {
  return (
    <div className="relative mx-auto w-full max-w-[620px] lg:ml-auto" aria-hidden="true">
      <div className="absolute inset-8 rotate-[-5deg] border border-accent/20 bg-[#EAF1EB]" />
      <svg viewBox="0 0 620 440" fill="none" className="relative block w-full text-accent">
        <path d="m28 110 165-60 135 44 105-45 152 69-31 251-160 28-134-46-152 45-90-73 10-213Z" fill="#EEF4EF" stroke="#0D624D" strokeOpacity=".45" strokeWidth="1.4" />
        <path d="m28 110 164 46 1-106m0 106 135-62 1 246m-136-184 136 66 164-98m-164 98 134 72m-270-138-1 183m137-117 163-98m-163 98 28 138m134-236 29 236M48 225l177-51 153 50 185-82M39 302l179-52 164 51 170-44" stroke="#0D624D" strokeOpacity=".3" strokeWidth="1.1" />
        <path d="m241 168 76-29 75 31-1 89-76 29-74-31v-89Z" fill="#DDBA54" fillOpacity=".24" stroke="#B98716" strokeWidth="2" />
        <path d="m250 180 65-24 61 25-1 71-61 24-64-27v-69Z" stroke="#B98716" strokeOpacity=".55" strokeDasharray="4 5" />
        <path d="M68 92 185 57m232 27 88 41M91 343l61 48m297-27 96-19" stroke="#0D624D" strokeOpacity=".35" strokeWidth="1.4" />
        <circle cx="316" cy="213" r="4" fill="#B98716" />
      </svg>
      <div className="absolute -bottom-2 left-2 border-l-2 border-gold pl-3 text-xs leading-5 text-muted sm:left-8">
        জমির নকশার রেখা থেকে অনুপ্রাণিত অলঙ্করণ
      </div>
    </div>
  );
}

export default function HomePage() {
  return (
    <div className="space-y-20 pb-10 sm:space-y-24">
      <section className="grid items-center gap-8 border-b border-line pb-12 sm:gap-10 sm:pb-16 lg:grid-cols-[0.88fr_1.12fr] lg:gap-14">
        <div className="relative z-10 max-w-xl">
          <p className="mb-5 flex items-center gap-3 text-sm font-semibold text-accent">
            <span className="h-px w-8 bg-gold" />
            জমির কাগজপত্র, এক জায়গায়
            <span className="rounded-full border border-gold/50 bg-gold/10 px-3 py-1 text-xs font-medium text-ink">{strings.pages.home.samplePill}</span>
          </p>
          <h1 className="max-w-lg text-4xl font-semibold leading-[1.2] tracking-tight text-ink sm:text-5xl lg:text-[3.6rem]">
            কেনার আগে নথির তথ্য মিলিয়ে নিন
          </h1>
          <p className="mt-5 max-w-lg text-base leading-8 text-muted sm:text-lg">
            খতিয়ান, দলিল ও নামজারির তথ্য পাশাপাশি দেখুন। অমিল পেলে কোন নথিতে কী আছে এবং এরপর কী যাচাই করবেন তা জানুন।
          </p>
          <div className="mt-7 flex flex-wrap items-center gap-x-6 gap-y-3">
            <Link href="/upload" className="inline-flex min-h-12 items-center justify-center rounded-md bg-accent px-5 text-base font-semibold text-white transition-colors hover:bg-[#185541] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
              যাচাই শুরু করুন
            </Link>
            <a href="#how-it-works" className="inline-flex min-h-11 items-center text-sm font-semibold text-accent underline decoration-gold decoration-2 underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
              কাজের পদ্ধতি
            </a>
          </div>
        </div>

        <ParcelStudy />
      </section>

      <section aria-labelledby="demo-title" className="rounded-2xl border border-line bg-surface p-5 sm:p-8">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-accent">JomiGuard</p>
            <h2 id="demo-title" className="mt-1 text-2xl font-semibold text-ink sm:text-3xl">{strings.pages.home.demoTitle}</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">{strings.pages.home.demoDesc}</p>
          </div>
          <p className="text-xs text-muted">{strings.pages.home.demoLoginNote}</p>
        </div>
        <ul className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {demoLinks.map(({ label, href }) => (
            <li key={href}>
              <Link href={href} className="flex min-h-12 items-center justify-between gap-3 rounded-lg border border-line px-4 py-3 text-sm font-semibold text-accent transition-colors hover:bg-accent-soft focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
                <span>{strings.pages.home[label]}</span><span aria-hidden="true">→</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="services-title" className="grid gap-8 lg:grid-cols-[0.75fr_1.25fr] lg:gap-16">
        <div className="max-w-md">
          <p className="mb-4 flex items-center gap-3 text-sm font-semibold text-accent">
            <span className="h-px w-8 bg-gold" />
            প্রয়োজন অনুযায়ী
          </p>
          <h2 id="services-title" className="text-3xl font-semibold leading-snug tracking-tight text-ink sm:text-4xl">
            জমি কেনার আগে থেকে মালিকানা নজরদারি পর্যন্ত
          </h2>
          <p className="mt-4 text-base leading-7 text-muted">
            কাগজ যাচাই, মালিকানার নথিভিত্তিক ইতিহাস, বায়না Escrow এবং খতিয়ান পর্যবেক্ষণ।
          </p>
          <Link href="/upload" className="mt-6 inline-flex min-h-11 items-center text-sm font-semibold text-accent underline decoration-gold decoration-2 underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
            কাগজ যাচাই শুরু করুন
          </Link>
        </div>

        <ul className="divide-y divide-line border-y border-line">
          {services.map((service) => (
            <li key={service.title}>
              <Link href={service.href} className="group grid min-h-24 gap-1 py-4 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent sm:grid-cols-[150px_1fr_24px] sm:items-center sm:gap-5 sm:py-5">
                <span className="text-xs font-medium text-muted">{service.tag}</span>
                <span>
                  <span className="block text-lg font-semibold text-ink group-hover:text-accent">{service.title}</span>
                  <span className="mt-1 block text-sm leading-6 text-muted">{service.detail}</span>
                </span>
                <span aria-hidden="true" className="hidden text-lg text-gold transition-transform group-hover:translate-x-1 sm:block">→</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <section id="how-it-works" aria-labelledby="steps-title" className="border-t border-line pt-10 sm:pt-12">
        <div className="grid gap-8 lg:grid-cols-[0.75fr_1.25fr] lg:gap-16">
          <div className="max-w-md">
            <p className="mb-4 flex items-center gap-3 text-sm font-semibold text-accent">
              <span className="h-px w-8 bg-gold" />
              যাচাইয়ের ধাপ
            </p>
            <h2 id="steps-title" className="text-3xl font-semibold leading-snug tracking-tight text-ink sm:text-4xl">
              নথি থেকে পরের করণীয়
            </h2>
          </div>
          <ol className="divide-y divide-line border-y border-line">
            <li className="grid gap-2 py-5 sm:grid-cols-[44px_1fr] sm:gap-4">
              <span className="font-mono text-sm text-gold">০১</span>
              <div><h3 className="font-semibold text-ink">জমির পরিচিতি দিন</h3><p className="mt-1 text-sm leading-6 text-muted">মৌজা ও দাগের তথ্য দিয়ে যাচাই শুরু করুন।</p></div>
            </li>
            <li className="grid gap-2 py-5 sm:grid-cols-[44px_1fr] sm:gap-4">
              <span className="font-mono text-sm text-gold">০২</span>
              <div><h3 className="font-semibold text-ink">সংশ্লিষ্ট কাগজ যোগ করুন</h3><p className="mt-1 text-sm leading-6 text-muted">খতিয়ান, দলিল বা নামজারির কপি দিন।</p></div>
            </li>
            <li className="grid gap-2 py-5 sm:grid-cols-[44px_1fr] sm:gap-4">
              <span className="font-mono text-sm text-gold">০৩</span>
              <div><h3 className="font-semibold text-ink">মিল ও অমিল পর্যালোচনা করুন</h3><p className="mt-1 text-sm leading-6 text-muted">প্রতিটি তথ্যের উৎস এবং পরের যাচাইয়ের ধাপ দেখুন।</p></div>
            </li>
          </ol>
        </div>
      </section>
    </div>
  );
}
