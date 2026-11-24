import Link from "next/link";
import { strings } from "@/lib/strings";
import { stringsEn } from "@/lib/strings-en";
import { T } from "@/lib/lang";

export default function OfflinePage() {
  return (
    <section className="mx-auto max-w-xl space-y-4 py-16 text-center">
      <h1 className="text-2xl font-semibold"><T bn={strings.error.offlineTitle} en={stringsEn.error.offlineTitle} /></h1>
      <p className="text-sm leading-6 text-muted"><T bn={strings.error.offlineMessage} en={stringsEn.error.offlineMessage} /></p>
      <Link href="/" className="inline-flex min-h-11 items-center rounded-lg border border-line px-5 font-semibold"><T bn={strings.error.homeLink} en={stringsEn.error.homeLink} /></Link>
    </section>
  );
}
