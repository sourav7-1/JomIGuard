import Link from "next/link";
import { strings } from "@/lib/strings";

export default function NotFound() {
  return (
    <section className="mx-auto max-w-xl space-y-4 py-16 text-center">
      <p className="font-mono text-sm text-accent">404</p>
      <h1 className="text-2xl font-semibold">{strings.error.notFoundTitle}</h1>
      <p className="text-sm leading-6 text-muted">{strings.error.notFoundMessage}</p>
      <Link href="/" className="inline-flex min-h-11 items-center rounded-lg bg-accent px-5 font-semibold text-white">{strings.error.homeLink}</Link>
    </section>
  );
}
