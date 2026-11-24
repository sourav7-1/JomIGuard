import Link from "next/link";
import { strings } from "@/lib/strings";
import { stringsEn } from "@/lib/strings-en";
import { T } from "@/lib/lang";

export default function NotFound() {
  return (
    <section className="mx-auto max-w-xl space-y-4 py-16 text-center">
      <p className="font-mono text-sm text-accent">404</p>
      <h1 className="text-2xl font-semibold"><T bn={strings.error.notFoundTitle} en={stringsEn.error.notFoundTitle} /></h1>
      <p className="text-sm leading-6 text-muted"><T bn={strings.error.notFoundMessage} en={stringsEn.error.notFoundMessage} /></p>
      <Link href="/" className="inline-flex min-h-11 items-center rounded-lg bg-accent px-5 font-semibold text-white"><T bn={strings.error.homeLink} en={stringsEn.error.homeLink} /></Link>
    </section>
  );
}
