import Link from "next/link";
import { strings } from "@/lib/strings";
import { BHOLA_CASE, officialLinks } from "@/lib/services";
import { Card } from "@/components/ui/Card";
import { PHASE_LABELS, STEP_LABELS, type Phase, type StepKey } from "@/lib/journey";
import { BholaPreview, bn } from "@/components/BholaPreview";
import { T } from "@/lib/lang";

const h = strings.pages.home;
const phases: Phase[] = ["before", "during", "after"];
const steps: { key: StepKey; phase: Phase; bn: string; en: string }[] = [
  { key: "location", phase: "before", bn: "মৌজা ও দাগ দিয়ে জমি খুঁজুন", en: "Find the plot by mouza and dag" },
  { key: "documents", phase: "before", bn: "খতিয়ান, দলিল, নামজারির ছবি দিন", en: "Add photos of khatian, deed, mutation" },
  { key: "paper", phase: "before", bn: "কাগজের নাম, দাগ ও পরিমাণ মেলানো", en: "Names, dag and area are cross-checked" },
  { key: "ground", phase: "before", bn: "স্যাটেলাইটে পানি ও গাছের বদল", en: "Water and tree changes from satellite" },
  { key: "report", phase: "before", bn: "কী মিলেছে, কী মেলেনি, এরপর কী", en: "What matched, what did not, what next" },
  { key: "seller", phase: "during", bn: "যাচাই সেবার মাধ্যমে বিক্রেতার পরিচয়", en: "Seller identity through a verification provider" },
  { key: "escrow", phase: "during", bn: "বায়নার টাকা ব্যাংকে, শর্ত মিললে ছাড়", en: "Earnest money held by a bank, released on conditions" },
  { key: "guardian", phase: "after", bn: "প্রতি মাসে খতিয়ানের বদলের খবর", en: "Monthly alert if the khatian changes" },
];

const primary = "inline-flex min-h-12 items-center justify-center rounded-[var(--radius-control)] bg-gradient-to-b from-accent to-[#23317A] px-5 text-base font-semibold text-white shadow-raised transition-transform hover:-translate-y-0.5";

export default function HomePage() {
  return (
    <div className="space-y-14 pb-10 sm:space-y-16">
      <section className="hero-glow grid items-center gap-10 border-b border-line pb-12 lg:grid-cols-[1.1fr_0.9fr] lg:gap-14">
        <div className="animate-fade-up relative z-10 max-w-2xl">
          <p className="mb-4 flex flex-wrap items-center gap-3 text-sm font-semibold text-accent">
            <span className="h-px w-8 bg-gold" />
            <T bn="জমি কেনার আগে, সময়ে ও পরে" en="Before, while and after you buy land" />
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
            <Link href="/how-it-works" className="inline-flex min-h-12 items-center text-base font-semibold text-accent underline decoration-gold underline-offset-4"><T bn="কীভাবে কাজ করে" en="How it works" /></Link>
          </div>
        </div>
        <BholaPreview />
      </section>

      <section data-tour="journey" aria-labelledby="journey-title" className="space-y-6">
        <div>
          <h2 id="journey-title" className="text-3xl font-semibold tracking-tight text-ink sm:text-4xl"><T bn="এক জমি, আট ধাপ" en="One plot, eight steps" /></h2>
          <p className="mt-2 text-sm leading-6 text-muted"><T bn="প্রতিটি কেস এই পথ ধরে চলে; কোন ধাপ বাকি, অ্যাপ তা দেখায়।" en="Every case follows this path; the app shows which step is still open." /></p>
        </div>
        <ol className="grid gap-4 lg:grid-cols-3">
          {phases.map((phase) => (
            <li key={phase} className="rounded-[var(--radius-card)] border border-line bg-surface p-5 shadow-rest">
              <p className="text-sm font-semibold text-accent"><T bn={PHASE_LABELS[phase].bn} en={PHASE_LABELS[phase].en} /></p>
              <ol className="mt-4 space-y-4 border-l-2 border-gold/50 pl-5">
                {steps.filter((s) => s.phase === phase).map((s) => {
                  const n = steps.indexOf(s) + 1;
                  return (
                    <li key={s.key} className="relative">
                      <span aria-hidden="true" className="absolute -left-[33px] top-0 inline-flex h-6 w-6 items-center justify-center rounded-full border-2 border-accent bg-surface text-xs font-bold text-accent"><T bn={bn(n)} en={String(n)} /></span>
                      <p className="font-semibold text-ink"><T bn={STEP_LABELS[s.key].bn} en={STEP_LABELS[s.key].en} /></p>
                      <p className="text-sm leading-6 text-muted"><T bn={s.bn} en={s.en} /></p>
                    </li>
                  );
                })}
              </ol>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="example-title" className="space-y-4">
        <h2 id="example-title" className="text-2xl font-semibold text-ink sm:text-3xl"><T bn="একটি উদাহরণ" en="An example" /></h2>
        <ul>
          <Card as="li" data-tour="bhola" variant="interactive" href={BHOLA_CASE} className="!border-sat/40 !bg-sat-soft/50"
            title={<T bn={<>ভোলা · চর মেঘনা, দাগ {bn(417)}</>} en="Bhola · Char Meghna, dag 417" />}
            meta={<span className="rounded-full bg-sat px-2.5 py-0.5 text-xs font-semibold text-white">★ <T bn="স্যাটেলাইট" en="Satellite" /></span>}
            description={<T bn="খতিয়ানে জমি 'নাল', কিন্তু শুকনো মৌসুমেও আশেপাশে পানি, আর ২০১৯ থেকে পানি বছর বছর বাড়ছে।" en="The khatian lists the land as 'nal' (cropland), yet there is water around it even in the dry season, and it has grown every year since 2019." />} />
        </ul>
        <p className="text-sm text-muted"><T bn={h.demoLoginNote} en="Login first to open the sample links." /> <Link href="/demo" className="font-semibold text-accent underline underline-offset-4"><T bn="আরো নমুনা কেস" en="More sample cases" /></Link></p>
      </section>

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
