"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, LandOut } from "@/lib/api";
import { Card, IconTile } from "@/components/ui/Card";
import { ListSkeleton } from "@/components/ui/Skeleton";
import { ServiceGrid } from "@/components/ServiceGrid";
import { ServiceIcon } from "@/components/ServiceIcon";
import { isListedLand } from "@/lib/bd-locations";
import { bnDigits } from "@/lib/digits";
import { useLang } from "@/lib/lang";

// Every page reachable from the dashboard (case/escrow detail pages open from their lists).
const pages = [
  { bn: "কেস তালিকা", en: "My cases", dbn: "আপনার সব জমির কেস", den: "All your land cases", href: "/cases", icon: "M4 6h16 M4 12h16 M4 18h10" },
  { bn: "কেস খুঁজুন / নতুন", en: "Find / new case", dbn: "মৌজা ও দাগ দিয়ে খুঁজুন", den: "Search by mouza and dag", href: "/find", icon: "M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14Z M20 20l-4-4" },
  { bn: "কাগজ আপলোড", en: "Upload documents", dbn: "খতিয়ান, দলিল, নামজারি", den: "Khatian, deed, mutation", href: "/upload", icon: "M12 16V4 M7 9l5-5 5 5 M4 20h16" },
  { bn: "বায়না escrow", en: "Bayna escrow", dbn: "শর্তসাপেক্ষে বায়নার টাকা", den: "Earnest money on conditions", href: "/escrow", icon: "M3 8h18v11H3z M3 11h18 M7 15h4" },
  { bn: "প্রবাসী গার্ডিয়ান", en: "Probashi guardian", dbn: "খতিয়ানের মাসিক নজরদারি", den: "Monthly khatian watch", href: "/guardian", icon: "M12 3 20 6v5c0 5-3.4 8.2-8 10-4.6-1.8-8-5-8-10V6z" },
  { bn: "জমি সহকারী AI", en: "Land AI assistant", dbn: "প্রশ্ন করুন", den: "Ask a question", href: "/chat", icon: "M4 5.5A2.5 2.5 0 0 1 6.5 3h11A2.5 2.5 0 0 1 20 5.5v8a2.5 2.5 0 0 1-2.5 2.5H11l-5 4v-4.3A2.5 2.5 0 0 1 4 13.5z" },
  { bn: "পরিচয় যাচাই", en: "Identity check", dbn: "ক্রেতার পরিচয়ের ফল", den: "Buyer verification result", href: "/profile", icon: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z M4 21a8 8 0 0 1 16 0" },
  { bn: "নমুনা ডেটা", en: "Demo data", dbn: "নমুনা কেস চালু করুন", den: "Load sample cases", href: "/demo", icon: "M4 7h16v12H4z M8 7V4h8v3" },
  { bn: "কীভাবে কাজ করে", en: "How it works", dbn: "ধাপে ধাপে ব্যাখ্যা", den: "Step-by-step explainer", href: "/how-it-works", icon: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Z M12 8v5 M12 16.5v.01" },
  { bn: "ডকস", en: "Docs", dbn: "নথির ধরন ও শব্দার্থ", den: "Document types and terms", href: "/docs", icon: "M6 3.75h8l4 4v12.5H6z M14 3.75v4h4" },
  { bn: "সাহায্য", en: "Help", dbn: "প্রশ্নোত্তর", den: "FAQ", href: "/help", icon: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z M12 17h.01" },
];

export default function DashboardPage() {
  const en = useLang() === "en";
  const t = (b: string, e: string) => (en ? e : b);
  const num = (v: string | number) => (en ? String(v) : bnDigits(v));
  const [user, setUser] = useState("");
  const [lands, setLands] = useState<LandOut[] | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    api.getMe().then((me) => setUser(me.username)).catch(() => undefined);
    api.getLands().then((rows) => setLands(rows.filter(isListedLand))).catch(() => setError(true));
  }, []);

  return (
    <div className="space-y-12">
      <section className="flex flex-col gap-5 border-b border-line pb-7 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="mb-3 flex items-center gap-3 text-sm font-semibold text-accent"><span className="h-px w-8 bg-gold" />{t("ড্যাশবোর্ড", "Dashboard")}</p>
          <h1 className="text-3xl font-semibold tracking-tight text-ink sm:text-4xl">{user ? t(`স্বাগতম, ${user}`, `Welcome, ${user}`) : t("স্বাগতম", "Welcome")}</h1>
          <p className="mt-3 text-base leading-7 text-muted">{t("এখান থেকে আপনার কেস, সেবা আর সব পাতা দেখুন।", "See your cases, services and every page from here.")}</p>
        </div>
        <Link href="/find" className="inline-flex min-h-11 shrink-0 items-center justify-center rounded-[var(--radius-control)] bg-accent px-4 text-sm font-semibold text-white shadow-rest">{t("নতুন যাচাই শুরু করুন", "Start a new check")}</Link>
      </section>

      <section aria-labelledby="my-cases" className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2 id="my-cases" className="text-2xl font-semibold text-ink">
            {t("আমার কেস", "My cases")}{lands && <span className="ml-2 text-base font-normal text-muted">({num(lands.length)})</span>}
          </h2>
          <Link href="/cases" className="inline-flex min-h-11 items-center text-sm font-semibold text-accent underline decoration-gold underline-offset-4">{t("সব কেস দেখুন", "See all cases")} →</Link>
        </div>
        {error ? <p role="alert" className="text-sm text-bad">{t("কেস তালিকা আনা যায়নি।", "Could not load your cases.")}</p>
          : lands === null ? <ListSkeleton />
          : lands.length === 0 ? <p className="text-sm text-muted">{t("এখনো কোনো কেস নেই। নতুন যাচাই শুরু করুন বা নমুনা ডেটা চালু করুন।", "No cases yet. Start a new check or load the demo data.")}</p>
          : <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{lands.slice(0, 6).map((land) => (
            <Card key={land.id} as="li" variant="interactive" href={`/cases/${land.id}`}
              title={<>{land.mouza || t("মৌজার তথ্য নেই", "No mouza")} · {t("দাগ", "dag")} {num(land.dag_no || "—")}</>}
              description={<>{[land.upazila, land.district].filter(Boolean).join(", ")} · {t("খতিয়ান", "khatian")} {num(land.khatian_no || "—")}</>} />
          ))}</ul>}
      </section>

      <section aria-labelledby="services" className="space-y-4">
        <h2 id="services" className="text-2xl font-semibold text-ink">{t("সেবাসমূহ", "Services")}</h2>
        <ServiceGrid />
      </section>

      <section aria-labelledby="all-pages" className="space-y-4">
        <h2 id="all-pages" className="text-2xl font-semibold text-ink">{t("সব পাতা", "All pages")}</h2>
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {pages.map((p) => (
            <Card key={p.href} as="li" variant="interactive" href={p.href}
              icon={<IconTile><ServiceIcon path={p.icon} /></IconTile>}
              title={t(p.bn, p.en)} description={t(p.dbn, p.den)} />
          ))}
        </ul>
      </section>
    </div>
  );
}
