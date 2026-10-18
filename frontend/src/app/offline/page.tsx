import Link from "next/link";
import { strings } from "@/lib/strings";

export default function OfflinePage() {
  return (
    <section className="mx-auto max-w-xl space-y-4 py-16 text-center">
      <h1 className="text-2xl font-semibold">{strings.error.offlineTitle}</h1>
      <p className="text-sm leading-6 text-muted">{strings.error.offlineMessage}</p>
      <Link href="/" className="inline-flex min-h-11 items-center rounded-lg border border-line px-5 font-semibold">{strings.error.homeLink}</Link>
    </section>
  );
}
