"use client";

import Link from "next/link";
import { T } from "@/lib/lang";
import { startTour } from "@/components/GuidedTour";

const ghost = "inline-flex min-h-12 items-center justify-center rounded-[var(--radius-control)] border border-accent/25 bg-surface/80 px-4 py-1.5 text-sm font-semibold text-ink shadow-rest transition hover:-translate-y-0.5 hover:shadow-raised";

export function JudgeBanner() {
  return (
    <section aria-labelledby="judge-title" className="surface-grad relative overflow-hidden rounded-[var(--radius-card)] border border-accent/25 bg-surface p-5 shadow-raised before:absolute before:inset-x-0 before:top-0 before:h-1 before:bg-gradient-to-r before:from-accent before:to-sat sm:p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 id="judge-title" className="font-heading text-2xl font-bold text-ink"><T bn="বিচারক? ৫ মিনিটে দেখে নিন" en="Judge? See it in 5 minutes" /></h2>
          <p className="mt-2 max-w-xl text-sm leading-6 text-muted"><T bn="৭ ধাপের গাইড মূল অংশগুলো দেখাবে; তারপর নমুনা ডেটা দিয়ে নিজে চেষ্টা করুন।" en="A 7-step guide, then try it yourself with demo data." /></p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => startTour()} className="inline-flex min-h-12 items-center justify-center rounded-[var(--radius-control)] bg-accent px-4 py-1.5 text-sm font-semibold text-white shadow-raised transition hover:-translate-y-0.5"><T bn="গাইড শুরু করুন" en="Start guide" /></button>
          <Link href="/demo" className={ghost}><T bn="নমুনা ডেটা" en="Demo data" /></Link>
          <Link href="/how-it-works" className={ghost}><T bn="কীভাবে কাজ করে" en="How it works" /></Link>
        </div>
      </div>
    </section>
  );
}
