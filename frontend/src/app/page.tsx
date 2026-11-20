import Link from "next/link";
import { strings } from "@/lib/strings";
import { BHOLA_CASE, officialLinks, services } from "@/lib/services";
import { ServiceIcon } from "@/components/ServiceIcon";

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
      <div className="absolute inset-8 rotate-[-5deg] border border-accent/20 bg-[#ECEEF7]" />
      <svg viewBox="0 0 620 440" fill="none" className="relative block w-full text-accent">
        <path d="m28 110 165-60 135 44 105-45 152 69-31 251-160 28-134-46-152 45-90-73 10-213Z" fill="#F1F2F9" stroke="#2D3E8F" strokeOpacity=".45" strokeWidth="1.4" />
        <path d="m28 110 164 46 1-106m0 106 135-62 1 246m-136-184 136 66 164-98m-164 98 134 72m-270-138-1 183m137-117 163-98m-163 98 28 138m134-236 29 236M48 225l177-51 153 50 185-82M39 302l179-52 164 51 170-44" stroke="#2D3E8F" strokeOpacity=".3" strokeWidth="1.1" />
        <path d="m241 168 76-29 75 31-1 89-76 29-74-31v-89Z" fill="#D98E63" fillOpacity=".24" stroke="#A4502A" strokeWidth="2" />
        <path d="m250 180 65-24 61 25-1 71-61 24-64-27v-69Z" stroke="#A4502A" strokeOpacity=".55" strokeDasharray="4 5" />
        <path d="M68 92 185 57m232 27 88 41M91 343l61 48m297-27 96-19" stroke="#2D3E8F" strokeOpacity=".35" strokeWidth="1.4" />
        <circle cx="316" cy="213" r="4" fill="#A4502A" />
      </svg>
      <div className="absolute -bottom-2 left-2 border-l-2 border-gold pl-3 text-xs leading-5 text-muted sm:left-8">
        জমির নকশার রেখা থেকে অনুপ্রাণিত অলঙ্করণ
      </div>
    </div>
  );
}

export default function HomePage() {
  return (
    <div className="space-y-14 pb-10 sm:space-y-16">
      <section className="grid items-center gap-8 border-b border-line pb-10 sm:gap-10 sm:pb-12 lg:grid-cols-[1fr_0.9fr] lg:gap-14">
        <div className="relative z-10 max-w-xl">
          <p className="mb-4 flex flex-wrap items-center gap-3 text-sm font-semibold text-accent">
            <span className="h-px w-8 bg-gold" />
            জমি কেনার আগে তিন ধাপ
            <span className="rounded-full border border-gold/50 bg-gold/10 px-3 py-1 text-xs font-medium text-ink">{strings.pages.home.samplePill}</span>
          </p>
          <h1 className="text-4xl font-semibold leading-[1.25] tracking-tight text-ink sm:text-5xl lg:text-[3.3rem]">
            কাগজ যাচাই, মাটি যাচাই, তারপর কিনুন
          </h1>
          <p className="mt-5 max-w-lg text-base leading-8 text-muted sm:text-lg">
            খতিয়ান, দলিল ও নামজারির তথ্য মিলিয়ে দেখুন, স্যাটেলাইট ছবিতে জমির আশেপাশে পানি ও গাছের বদল দেখুন, আর জেনে নিন এরপর কী যাচাই করবেন।
          </p>
          <div className="mt-7 flex flex-wrap items-center gap-3">
            <Link href="/find" className="inline-flex min-h-12 items-center justify-center rounded-[var(--radius-control)] bg-accent px-5 text-base font-semibold text-white transition-colors hover:bg-[#23317A]">
              কেস খুঁজুন বা নতুন কেস
            </Link>
            <Link href={BHOLA_CASE} className="inline-flex min-h-12 items-center justify-center rounded-[var(--radius-control)] border border-sat/40 bg-sat-soft px-5 text-base font-semibold text-sat transition-colors hover:border-sat">
              ভোলার স্যাটেলাইট নমুনা দেখুন
            </Link>
          </div>
        </div>
        <ParcelStudy />
      </section>

      <section aria-labelledby="services-title" className="space-y-5">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2 id="services-title" className="text-3xl font-semibold tracking-tight text-ink sm:text-4xl">সেবাসমূহ</h2>
          <Link href="/help" className="inline-flex min-h-11 items-center text-sm font-semibold text-accent underline decoration-gold decoration-2 underline-offset-4">কীভাবে ব্যবহার করবেন?</Link>
        </div>
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {services.map((s) => (
            <li key={s.id}>
              <Link href={s.start.href} className={`group flex h-full flex-col rounded-[var(--radius-card)] border bg-surface p-5 shadow-[var(--shadow-card)] transition-colors ${s.satellite ? "border-sat/40 hover:border-sat" : "border-line hover:border-accent"}`}>
                <span className={`inline-flex h-12 w-12 items-center justify-center rounded-xl ${s.satellite ? "bg-sat-soft text-sat" : "bg-accent-soft text-accent"}`}>
                  <ServiceIcon path={s.icon} />
                </span>
                <span className="mt-4 text-xl font-semibold leading-snug text-ink">{s.title}</span>
                <span className="mt-1.5 flex-1 text-sm leading-7 text-muted">{s.line}</span>
                <span className={`mt-4 inline-flex min-h-11 w-fit items-center gap-2 rounded-[var(--radius-control)] px-4 text-sm font-semibold text-white ${s.satellite ? "bg-sat" : "bg-accent"}`}>
                  {s.start.label} <span aria-hidden="true" className="transition-transform group-hover:translate-x-0.5">→</span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="demo-title" className="rounded-[var(--radius-card)] border border-line bg-surface p-5 shadow-[var(--shadow-card)] sm:p-8">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 id="demo-title" className="text-2xl font-semibold text-ink sm:text-3xl">নমুনা কেস</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">{strings.pages.home.demoDesc}</p>
          </div>
          <p className="text-sm text-muted">{strings.pages.home.demoLoginNote}</p>
        </div>
        <Link href={BHOLA_CASE} className="group mt-6 grid gap-3 rounded-[var(--radius-card)] border border-sat/40 bg-sat-soft p-5 transition-colors hover:border-sat sm:grid-cols-[1fr_auto] sm:items-center">
          <span>
            <span className="text-xs font-semibold text-sat">★ স্যাটেলাইট যাচাইয়ের নমুনা</span>
            <span className="mt-1 block text-xl font-semibold text-ink">ভোলা · চর মেঘনা, দাগ ৪১৭</span>
            <span className="mt-1 block text-sm leading-6 text-muted">খতিয়ানে জমি &apos;নাল&apos;, কিন্তু শুকনো মৌসুমেও আশেপাশে পানি, আর ২০১৯ থেকে পানি বছর বছর বাড়ছে।</span>
          </span>
          <span className="inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-sat">কেস খুলুন <span aria-hidden="true" className="transition-transform group-hover:translate-x-1">→</span></span>
        </Link>
        <ul className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {demoLinks.map(({ label, href }) => (
            <li key={href}>
              <Link href={href} className="flex min-h-12 items-center justify-between gap-3 rounded-[var(--radius-control)] border border-line px-4 py-3 text-sm font-semibold text-accent transition-colors hover:bg-accent-soft">
                <span>{strings.pages.home[label]}</span><span aria-hidden="true">→</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="official-title" className="rounded-[var(--radius-card)] border border-dashed border-line bg-bg p-5 sm:p-6">
        <h2 id="official-title" className="text-xl font-semibold text-ink">সরকারি সেবা লাগলে</h2>
        <p className="mt-1 text-sm leading-6 text-muted">সার্টিফাইড খতিয়ান, নামজারি বা ভূমি উন্নয়ন কর আমাদের সেবা নয়; এগুলো সরকারি সাইট থেকে নিতে হয়।</p>
        <ul className="mt-4 grid gap-3 sm:grid-cols-3">
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
