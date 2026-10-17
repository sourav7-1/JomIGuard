import React, { Suspense } from "react";
import Link from "next/link";
import { ThemeToggle } from "./ThemeToggle";
import { JourneyRail } from "./JourneyRail";
import { strings } from "@/lib/strings";

export function Header() {
  return (
    <header className="w-full bg-surface/90 backdrop-blur-sm border-b border-line sticky top-0 z-40 transition-colors">
      <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between gap-4">
        <Link
          href="/"
          className="flex flex-col rounded-lg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent py-0.5"
        >
          <span className="text-xl md:text-2xl font-bold font-heading text-accent tracking-tight">
            {strings.app.name}
          </span>
          <span className="text-xs text-muted font-normal hidden xs:inline sm:inline">
            {strings.app.taglineShort}
          </span>
        </Link>

        <div className="flex items-center gap-2 sm:gap-3">
          <Link
            href="/upload"
            className="min-h-[44px] px-3.5 py-2 rounded-lg bg-accent text-white hover:opacity-90 transition-opacity flex items-center justify-center text-sm font-medium focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            {strings.buttons.upload}
          </Link>
          <Link
            href="/chat"
            className="min-h-[44px] min-w-[44px] px-3 py-2 rounded-lg border border-line bg-surface text-ink hover:bg-bg transition-colors flex items-center justify-center text-sm font-medium focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            aria-label={strings.nav.chat}
          >
            💬
          </Link>
          <ThemeToggle />
        </div>
      </div>

      <Suspense fallback={<div className="w-full max-w-5xl mx-auto px-4 py-3 min-h-[72px]" />}>
        <JourneyRail />
      </Suspense>
    </header>
  );
}
