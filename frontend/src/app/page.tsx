import Link from "next/link";
import { strings } from "@/lib/strings";
import { BHOLA_CASE, officialLinks } from "@/lib/services";
import { Card } from "@/components/ui/Card";
import { ServiceGrid } from "@/components/ServiceGrid";
import { JudgeBanner } from "@/components/JudgeBanner";
import { BholaPreview, bn } from "@/components/BholaPreview";
import { T } from "@/lib/lang";

const h = strings.pages.home;
const demoLinks = [
  { bn: h.demoCase1, en: "Case 00001 · high risk", href: "/cases/66c09208-d737-59f0-937e-de349f50899a" },
  { bn: h.demoCase26, en: "Case 00026 · ordinary sale", href: "/cases/6c530a00-cc5c-5c6b-a341-ae4491761d4e" },
  { bn: h.demoDeedArchive26, en: "Case 00026 · earlier deeds and evidence", href: "/cases/6c530a00-cc5c-5c6b-a341-ae4491761d4e#deed-archive-title" },
  { bn: h.demoCase29, en: "Case 00029 · family case", href: "/cases/801bc1b6-b43c-5147-9b4f-b0baa3815cd0" },
  { bn: h.demoTimeline29, en: "Case 00029 · land history", href: "/cases/801bc1b6-b43c-5147-9b4f-b0baa3815cd0/timeline" },
  { bn: h.demoGuardian, en: "Probashi guardian", href: "/guardian" },
  { bn: h.demoEscrow26, en: "Case 00026 · bayna escrow", href: "/escrow/demo-00026" },
];

const primary = "inline-flex min-h-12 items-center justify-center rounded-[var(--radius-control)] bg-gradient-to-b from-accent to-[#23317A] px-5 text-base font-semibold text-white shadow-raised transition-transform hover:-translate-y-0.5";
const secondary = "inline-flex min-h-12 items-center justify-center rounded-[var(--radius-control)] border border-sat/40 bg-sat-soft/80 px-5 text-base font-semibold text-sat shadow-rest transition-colors hover:border-sat";

export default function HomePage() {
  return (
    <div className="space-y-14 pb-10 sm:space-y-16">
      <JudgeBanner />
      <section className="hero-glow grid items-center gap-10 border-b border-line pb-12 lg:grid-cols-[1.1fr_0.9fr] lg:gap-14">
        <div className="animate-fade-up relative z-10 max-w-2xl">
          <p className="mb-4 flex flex-wrap items-center gap-3 text-sm font-semibold text-accent">
            <span className="h-px w-8 bg-gold" />
            <T bn="জমি কেনার আগে তিন ধাপ" en="Three steps before you buy land" />
            <span className="rounded-full border border-gold/40 bg-surface/70 px-3 py-1 text-xs font-medium text-ink"><T bn={h.samplePill} en="All names and numbers are samples" /></span>
          </p>
          <h1 className="text-[2.6rem] font-semibold leading-[1.2] tracking-tight text-ink sm:text-6xl lg:text-[4.1rem]">
            <T bn={<>কাগজ যাচাই, <span className="text-gradient">মাটি যাচাই</span>, তারপর কিনুন</>} en={<>Check the papers, <span className="text-gradient">check the ground</span>, then buy</>} />
          </h1>
          <p className="mt-6 max-w-xl text-base leading-8 text-muted sm:text-lg">
            <T
              bn="খতিয়ান, দলিল ও নামজারির তথ্য মিলিয়ে দেখুন, স্যাটেলাইট ছবিতে জমির আশেপাশে পানি ও গাছের বদল দেখুন, আর জেনে নিন এরপর কী যাচাই করবেন।"
              en="Cross-check khatian, deed and mutation data, see water and tree changes around the plot in satellite images, and learn what to check next."
            />
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link href="/login" className={primary}><T bn="প্রবেশ করে শুরু করুন" en="Login to get started" /></Link>
            <Link href={BHOLA_CASE} className={secondary}><T bn="ভোলার স্যাটেলাইট নমুনা দেখুন" en="See the Bhola satellite sample" /></Link>
          </div>
        </div>
        <BholaPreview />
      </section>

      <section aria-labelledby="services-title" className="space-y-5">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2 id="services-title" className="text-3xl font-semibold tracking-tight text-ink sm:text-4xl"><T bn="সেবাসমূহ" en="Services" /></h2>
          <Link href="/help" className="inline-flex min-h-11 items-center text-sm font-semibold text-accent underline decoration-gold decoration-2 underline-offset-4"><T bn="সব সাহায্য ও প্রশ্নোত্তর" en="All help and FAQ" /></Link>
        </div>
        <ServiceGrid />
      </section>

      <Card as="section" aria-labelledby="demo-title" className="p-5 sm:p-8">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 id="demo-title" className="text-2xl font-semibold text-ink sm:text-3xl"><T bn="নমুনা কেস" en="Sample cases" /></h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted"><T bn={h.demoDesc} en="See the check, history, monitoring and bayna flows with sample cases." /></p>
          </div>
          <p className="text-sm text-muted"><T bn={h.demoLoginNote} en="Login first to open the sample links." /></p>
        </div>
        <ul className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Card as="li" data-tour="bhola" variant="interactive" href={BHOLA_CASE} className="!border-sat/40 !bg-sat-soft/50 sm:col-span-2 lg:col-span-3"
            title={<T bn={<>ভোলা · চর মেঘনা, দাগ {bn(417)}</>} en="Bhola · Char Meghna, dag 417" />}
            meta={<span className="rounded-full bg-sat px-2.5 py-0.5 text-xs font-semibold text-white">★ <T bn="স্যাটেলাইট" en="Satellite" /></span>}
            description={<T bn="খতিয়ানে জমি 'নাল', কিন্তু শুকনো মৌসুমেও আশেপাশে পানি, আর ২০১৯ থেকে পানি বছর বছর বাড়ছে।" en="The khatian lists the land as 'nal' (cropland), yet there is water around it even in the dry season, and it has grown every year since 2019." />} />
          {demoLinks.map((d) => (
            <Card key={d.href} as="li" variant="interactive" href={d.href} padded={false} className="px-4 py-3"
              title={<span className="font-body text-base font-semibold text-accent"><T bn={d.bn} en={d.en} /></span>}
              meta={<span aria-hidden="true" className="text-accent">→</span>} />
          ))}
        </ul>
      </Card>

      <section aria-labelledby="official-title" className="rounded-[var(--radius-card)] border border-dashed border-line bg-bg p-5 sm:p-6">
        <h2 id="official-title" className="text-xl font-semibold text-ink"><T bn="সরকারি সেবা লাগলে" en="If you need a government service" /></h2>
        <p className="mt-1 text-sm leading-6 text-muted"><T bn="সার্টিফাইড খতিয়ান, নামজারি বা ভূমি উন্নয়ন কর আমাদের সেবা নয়; এগুলো সরকারি সাইট থেকে নিতে হয়।" en="Certified khatian, mutation and land development tax are not our services; get them from the government sites." /></p>
        <ul className="mt-4 grid gap-3 sm:grid-cols-3">
          {officialLinks.map((l) => (
            <li key={l.href}>
              <a href={l.href} target="_blank" rel="noopener noreferrer" className="flex min-h-12 flex-col justify-center rounded-[var(--radius-control)] border border-line bg-surface px-4 py-2.5 shadow-rest hover:border-accent">
                <span className="text-sm font-semibold text-accent"><T bn={l.label} en={l.labelEn} /> <span aria-hidden="true">↗</span></span>
                <span className="text-xs text-muted"><T bn="সরকারি সাইট, আমাদের নয়" en="Government site, not ours" /></span>
              </a>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
