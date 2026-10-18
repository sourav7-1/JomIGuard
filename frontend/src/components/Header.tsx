import Link from "next/link";
import { Suspense } from "react";
import { ThemeToggle } from "./ThemeToggle";
import { JourneyRail } from "./JourneyRail";
import { strings } from "@/lib/strings";
import { AuthControls } from "@/components/AuthControls";

function ShieldMark() {
  return (
    <svg aria-hidden="true" viewBox="0 0 48 48" fill="none" className="h-10 w-10 shrink-0">
      <path d="M24 2 43 9v13c0 11-7.5 19-19 24C12.5 41 5 33 5 22V9L24 2Z" fill="#08745C" />
      <path d="M24 7 38 12v10c0 8-5.2 14.4-14 19.2C15.2 36.4 10 30 10 22V12L24 7Z" stroke="white" strokeWidth="1.8" />
      <path d="M24 7v13c0 4.5-2.3 7.2-6.5 8.5L10 31M24 25h5c2.2 0 3.7-1.2 4.8-3.3" stroke="white" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M28 27h9v4c0 4.1-2.7 7.2-8.1 10.1-1.4-.8-2.8-1.7-3.9-2.7V31c0-2.2 1-4 3-4Z" fill="#E2B52C" stroke="white" strokeWidth="1.5" />
      <path d="m28.8 33.2 2 2 4-4.4" stroke="white" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M34 5v7h7" stroke="white" strokeWidth="1.8" strokeLinejoin="round" />
    </svg>
  );
}

export function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-surface/95 backdrop-blur-md">
      <div className="mx-auto flex min-h-[68px] max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:min-h-[76px] lg:px-8">
        <Link href="/" className="flex min-w-0 items-center gap-2 rounded-lg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
          <ShieldMark />
          <span className="min-w-0">
            <span className="block font-heading text-xl font-bold leading-6 tracking-tight text-accent">{strings.app.name}</span>
            <span className="hidden text-xs leading-4 text-muted sm:block">কাগজের তথ্য মিলিয়ে দেখুন</span>
          </span>
        </Link>
        <div className="flex shrink-0 items-center gap-2 sm:gap-3">
          <Link href="/upload" className="inline-flex min-h-11 items-center justify-center rounded-md bg-accent px-3.5 text-sm font-semibold text-white transition-colors hover:bg-[#185541] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent sm:px-4">
            <span className="sm:hidden">যাচাই শুরু</span>
            <span className="hidden sm:inline">{strings.buttons.newCheck}</span>
          </Link>
          <ThemeToggle />
          <AuthControls />
        </div>
      </div>
      <Suspense fallback={<div className="h-14 md:h-12" />}>
        <JourneyRail />
      </Suspense>
    </header>
  );
}
