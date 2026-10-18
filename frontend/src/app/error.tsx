"use client";

import Link from "next/link";
import { strings } from "@/lib/strings";

export default function ErrorPage({ retry }: { error: Error & { digest?: string }; retry: () => void }) {
  return (
    <section className="mx-auto max-w-xl space-y-4 py-16 text-center">
      <h1 className="text-2xl font-semibold">{strings.error.serverErrorTitle}</h1>
      <p className="text-sm leading-6 text-muted">{strings.error.serverError}</p>
      <div className="flex flex-wrap justify-center gap-3">
        <button type="button" onClick={retry} className="min-h-11 rounded-lg bg-accent px-5 font-semibold text-white">{strings.error.retryPage}</button>
        <Link href="/offline" className="inline-flex min-h-11 items-center rounded-lg border border-line px-5 font-semibold">{strings.error.offlineTitle}</Link>
      </div>
    </section>
  );
}
