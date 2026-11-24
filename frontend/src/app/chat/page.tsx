"use client";

import Link from "next/link";
import { useLang, useStrings } from "@/lib/lang";

export default function ChatPage() {
  const strings = useStrings();
  const en = useLang() === "en";
  const t = (b: string, e: string) => (en ? e : b);
  return (
    <div className="mx-auto max-w-5xl space-y-10 py-2 sm:space-y-12">
      <header className="max-w-2xl border-b border-line pb-7">
        <p className="mb-3 flex items-center gap-3 text-sm font-semibold text-accent"><span className="h-px w-8 bg-gold" />{t("সহায়তা", "Help")}</p>
        <h1 className="text-3xl font-semibold leading-tight tracking-tight text-ink sm:text-4xl">{strings.pages.chat.title}</h1>
        <p className="mt-3 text-base leading-7 text-muted">{strings.pages.chat.desc}</p>
      </header>

      <section className="max-w-2xl border-l-2 border-gold pl-5 sm:pl-7">
        <h2 className="text-xl font-semibold text-ink">{t("জমির কাগজপত্র নিয়ে প্রশ্ন আছে?", "Questions about land papers?")}</h2>
        <p className="mt-2 text-sm leading-7 text-muted">{t("প্রশ্নের উত্তরে AI সহায়তা ব্যবহার করা হলে তথ্যটি সংশ্লিষ্ট নথি ও পেশাজীবীর পরামর্শ দিয়ে মিলিয়ে নিন।", "When an answer uses AI help, check it against the relevant documents and a professional's advice.")}</p>
        <Link href="/upload" className="mt-5 inline-flex min-h-11 items-center text-sm font-semibold text-accent underline decoration-gold decoration-2 underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">{t("কাগজ যাচাই শুরু করুন", "Start a document check")}</Link>
      </section>
    </div>
  );
}
