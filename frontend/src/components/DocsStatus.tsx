"use client";

import { useEffect, useState } from "react";
import { api, type DemoStatus } from "@/lib/api";
import { Skeleton } from "@/components/ui/Skeleton";
import { useLang } from "@/lib/lang";

const when = (iso: string | null) => (iso ? new Date(iso).toLocaleString("bn-BD", { dateStyle: "medium", timeStyle: "short" }) : "—");

// Read-only live status for /docs (backend/app/api/demo.py /demo/status).
export function DocsStatus() {
  const lang = useLang();
  const t = (b: string, e: string) => (lang === "en" ? e : b);
  const [s, setS] = useState<DemoStatus | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => { api.demoStatus().then(setS).catch(() => setError(true)); }, []);
  if (error) return <p role="alert" className="rounded-[var(--radius-control)] bg-bad-bg p-3 text-sm text-bad">{t("অবস্থা আনা যায়নি; ব্যাকএন্ড বন্ধ থাকতে পারে।", "Could not load status; the backend may be down.")}</p>;
  if (!s) return <div role="status" aria-label={t("অবস্থা লোড হচ্ছে", "Loading status")} className="grid gap-2 sm:grid-cols-2"><Skeleton className="h-14 w-full" /><Skeleton className="h-14 w-full" /><Skeleton className="h-14 w-full" /><Skeleton className="h-14 w-full" /></div>;
  const rows: [string, string, boolean | null, string?][] = [
    ["ব্যাকএন্ড", "Backend", s.backend],
    ["স্যাটেলাইট সার্ভিস", "Sentinel service", s.sentinel],
    ["Earth Engine", "Earth Engine", s.earth_engine, t("সর্বশেষ লাইভ যাচাই সফল কি না থেকে ধরা", "Based on whether the last live check succeeded")],
    ["সর্বশেষ স্যাটেলাইট যাচাই", "Last satellite check", null, when(s.last_check_at)],
  ];
  return (
    <ul className="grid gap-2 sm:grid-cols-2">
      {rows.map(([bn, en, ok, extra]) => (
        <li key={en} className="flex items-start gap-3 rounded-[var(--radius-control)] border border-edge bg-bg/60 p-3 text-sm">
          {ok !== null && <span aria-hidden="true" className={`mt-1 h-2.5 w-2.5 shrink-0 rounded-full ${ok ? "bg-ok" : "bg-bad"}`} />}
          <span><b>{lang === "en" ? en : bn}</b>{ok !== null && <>: {ok ? t("চালু", "up") : t("বন্ধ / সমস্যা", "down / problem")}</>}{extra && <span className="block text-xs text-muted">{extra}</span>}</span>
        </li>
      ))}
    </ul>
  );
}
