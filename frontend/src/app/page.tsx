import Link from "next/link";
import { strings } from "@/lib/strings";
import { BHOLA_CASE, officialLinks } from "@/lib/services";
import { Card } from "@/components/ui/Card";
import { ServiceGrid } from "@/components/ServiceGrid";
import { JudgeBanner } from "@/components/JudgeBanner";
import { BholaPreview, bn } from "@/components/BholaPreview";

const demoLinks = [
  { label: "demoCase1", href: "/cases/66c09208-d737-59f0-937e-de349f50899a" },
  { label: "demoCase26", href: "/cases/6c530a00-cc5c-5c6b-a341-ae4491761d4e" },
  { label: "demoDeedArchive26", href: "/cases/6c530a00-cc5c-5c6b-a341-ae4491761d4e#deed-archive-title" },
  { label: "demoCase29", href: "/cases/801bc1b6-b43c-5147-9b4f-b0baa3815cd0" },
  { label: "demoTimeline29", href: "/cases/801bc1b6-b43c-5147-9b4f-b0baa3815cd0/timeline" },
  { label: "demoGuardian", href: "/guardian" },
  { label: "demoEscrow26", href: "/escrow/demo-00026" },
] as const;

export default function HomePage() {
  return (
    <div className="space-y-14 pb-10 sm:space-y-16">
      <JudgeBanner />
      <section className="hero-glow grid items-center gap-10 border-b border-line pb-12 lg:grid-cols-[1.1fr_0.9fr] lg:gap-14">
        <div className="animate-fade-up relative z-10 max-w-2xl">
          <p className="mb-4 flex flex-wrap items-center gap-3 text-sm font-semibold text-accent">
            <span className="h-px w-8 bg-gold" />
            জমি কেনার আগে তিন ধাপ
            <span className="rounded-full border border-gold/40 bg-surface/70 px-3 py-1 text-xs font-medium text-ink">{strings.pages.home.samplePill}</span>
          </p>
          <h1 className="text-[2.6rem] font-semibold leading-[1.2] tracking-tight text-ink sm:text-6xl lg:text-[4.1rem]">
            কাগজ যাচাই, <span className="text-gradient">মাটি যাচাই</span>, তারপর কিনুন
          </h1>
          <p className="mt-6 max-w-xl text-base leading-8 text-muted sm:text-lg">
            খতিয়ান, দলিল ও নামজারির তথ্য মিলিয়ে দেখুন, স্যাটেলাইট ছবিতে জমির আশেপাশে পানি ও গাছের বদল দেখুন, আর জেনে নিন এরপর কী যাচাই করবেন।
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link href="/find" className="inline-flex min-h-12 items-center justify-center rounded-[var(--radius-control)] bg-gradient-to-b from-accent to-[#23317A] px-5 text-base font-semibold text-white shadow-raised transition-transform hover:-translate-y-0.5">
              কেস খুঁজুন বা নতুন কেস
            </Link>
            <Link href={BHOLA_CASE} className="inline-flex min-h-12 items-center justify-center rounded-[var(--radius-control)] border border-sat/40 bg-sat-soft/80 px-5 text-base font-semibold text-sat shadow-rest transition-colors hover:border-sat">
              ভোলার স্যাটেলাইট নমুনা দেখুন
            </Link>
          </div>
        </div>
        <BholaPreview />
      </section>

      <section aria-labelledby="services-title" className="space-y-5">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2 id="services-title" className="text-3xl font-semibold tracking-tight text-ink sm:text-4xl">সেবাসমূহ</h2>
          <Link href="/help" className="inline-flex min-h-11 items-center text-sm font-semibold text-accent underline decoration-gold decoration-2 underline-offset-4">সব সাহায্য ও প্রশ্নোত্তর</Link>
        </div>
        <ServiceGrid />
      </section>

      <Card as="section" aria-labelledby="demo-title" className="p-5 sm:p-8">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 id="demo-title" className="text-2xl font-semibold text-ink sm:text-3xl">নমুনা কেস</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">{strings.pages.home.demoDesc}</p>
          </div>
          <p className="text-sm text-muted">{strings.pages.home.demoLoginNote}</p>
        </div>
        <ul className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Card as="li" data-tour="bhola" variant="interactive" href={BHOLA_CASE} className="!border-sat/40 !bg-sat-soft/50 sm:col-span-2 lg:col-span-3"
            title={<>ভোলা · চর মেঘনা, দাগ {bn(417)}</>}
            meta={<span className="rounded-full bg-sat px-2.5 py-0.5 text-xs font-semibold text-white">★ স্যাটেলাইট</span>}
            description="খতিয়ানে জমি 'নাল', কিন্তু শুকনো মৌসুমেও আশেপাশে পানি, আর ২০১৯ থেকে পানি বছর বছর বাড়ছে।" />
          {demoLinks.map(({ label, href }) => (
            <Card key={href} as="li" variant="interactive" href={href} padded={false} className="px-4 py-3"
              title={<span className="font-body text-base font-semibold text-accent">{strings.pages.home[label]}</span>}
              meta={<span aria-hidden="true" className="text-accent">→</span>} />
          ))}
        </ul>
      </Card>

      <section aria-labelledby="official-title" className="rounded-[var(--radius-card)] border border-dashed border-line bg-bg p-5 sm:p-6">
        <h2 id="official-title" className="text-xl font-semibold text-ink">সরকারি সেবা লাগলে</h2>
        <p className="mt-1 text-sm leading-6 text-muted">সার্টিফাইড খতিয়ান, নামজারি বা ভূমি উন্নয়ন কর আমাদের সেবা নয়; এগুলো সরকারি সাইট থেকে নিতে হয়।</p>
        <ul className="mt-4 grid gap-3 sm:grid-cols-3">
          {officialLinks.map((l) => (
            <li key={l.href}>
              <a href={l.href} target="_blank" rel="noopener noreferrer" className="flex min-h-12 flex-col justify-center rounded-[var(--radius-control)] border border-line bg-surface px-4 py-2.5 shadow-rest hover:border-accent">
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
