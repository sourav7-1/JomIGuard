import Link from "next/link";
import { ThemeToggle } from "./ThemeToggle";
import { JourneyRail } from "./JourneyRail";
import { strings } from "@/lib/strings";

function ShieldMark() {
  return (
    <svg aria-hidden="true" viewBox="0 0 32 32" fill="none" className="h-9 w-9 shrink-0">
      <path d="M16 2.8 27 7v7.2c0 7.2-4.8 12-11 15-6.2-3-11-7.8-11-15V7z" fill="#12342A" />
      <path d="m10.5 16.2 3.4 3.3 7.6-8" stroke="#7FD1B3" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-surface/95 backdrop-blur-md">
      <div className="mx-auto flex min-h-[68px] max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <Link href="/" className="flex min-w-0 items-center gap-2 rounded-lg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
          <ShieldMark />
          <span className="min-w-0">
            <span className="block font-heading text-xl font-semibold leading-6 text-ink">{strings.app.name}</span>
            <span className="hidden text-xs leading-4 text-muted sm:block">কাগজের তথ্য মিলিয়ে দেখুন</span>
          </span>
        </Link>
        <div className="flex shrink-0 items-center gap-2">
          <Link href="/upload" className="inline-flex min-h-11 items-center justify-center rounded-lg bg-accent px-3.5 text-sm font-semibold text-white transition-colors hover:bg-[#185541] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent sm:px-4">
            {strings.buttons.newCheck}
          </Link>
          <ThemeToggle />
        </div>
      </div>
      <JourneyRail />
    </header>
  );
}
