import React from "react";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { strings } from "@/lib/strings";

const features = [
  {
    step: "ধাপ ১",
    title: strings.pages.home.feature1Title,
    desc: strings.pages.home.feature1Desc,
    href: "/cases",
    badge: "যাচাই ইঞ্জিন",
  },
  {
    step: "ধাপ ২",
    title: strings.pages.home.feature2Title,
    desc: strings.pages.home.feature2Desc,
    href: "/cases/demo/timeline",
    badge: "টাইমলাইন",
  },
  {
    step: "ধাপ ৩",
    title: strings.pages.home.feature3Title,
    desc: strings.pages.home.feature3Desc,
    href: "/escrow",
    badge: "ব্যাংক পার্টনার",
  },
  {
    step: "ধাপ ৪",
    title: strings.pages.home.feature4Title,
    desc: strings.pages.home.feature4Desc,
    href: "/guardian",
    badge: "মাসিক নজরদারি",
  },
];

export default function HomePage() {
  return (
    <div className="space-y-8 py-4">
      <section className="text-center space-y-3 max-w-2xl mx-auto">
        <h1 className="text-2xl md:text-4xl font-bold font-heading text-ink">
          {strings.pages.home.title}
        </h1>
        <p className="text-sm md:text-base text-muted leading-relaxed">
          {strings.pages.home.subtitle}
        </p>
        <div className="pt-2 flex flex-wrap items-center justify-center gap-3">
          <Link
            href="/upload"
            className="min-h-[44px] px-6 py-2.5 rounded-lg bg-accent text-white font-medium hover:opacity-90 transition-opacity flex items-center justify-center focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            {strings.buttons.newCheck}
          </Link>
          <Link
            href="/cases"
            className="min-h-[44px] px-5 py-2.5 rounded-lg border border-line bg-surface text-ink hover:bg-bg transition-colors flex items-center justify-center text-sm font-medium focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            {strings.buttons.viewDetails}
          </Link>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-lg md:text-xl font-bold font-heading text-ink">
          {strings.pages.home.fourFeaturesTitle}
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {features.map((f) => (
            <Link
              key={f.step}
              href={f.href}
              className="group block focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent rounded-xl"
            >
              <Card className="h-full transition-all group-hover:border-accent/50 group-hover:shadow-sm space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-semibold px-2 py-0.5 rounded bg-accent-soft text-accent">
                    {f.step}
                  </span>
                  <span className="text-xs text-muted font-mono">{f.badge}</span>
                </div>
                <h3 className="text-base font-bold font-heading text-ink group-hover:text-accent transition-colors">
                  {f.title}
                </h3>
                <p className="text-sm text-muted leading-relaxed">{f.desc}</p>
              </Card>
            </Link>
          ))}
        </div>
      </section>

      <section className="rounded-xl border border-line bg-surface p-5 space-y-2">
        <h3 className="text-base font-bold font-heading text-ink">
          {strings.pages.home.coreEngineTitle}
        </h3>
        <p className="text-sm text-muted leading-relaxed">
          {strings.pages.home.coreEngineDesc}
        </p>
      </section>
    </div>
  );
}
