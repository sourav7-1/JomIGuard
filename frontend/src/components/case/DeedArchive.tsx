"use client";

import React, { useState } from "react";
import Link from "next/link";
import { api, DeedArchiveItemOut, FingerprintVerificationOut } from "@/lib/api";
import { useLang, useStrings } from "@/lib/lang";

function archiveValue(value: unknown): string {
  if (value == null || value === "") return "—";
  if (Array.isArray(value)) {
    return value.map((item) => typeof item === "object" && item ? Object.values(item as Record<string, unknown>).filter(Boolean).join(" · ") : String(item)).join(", ") || "—";
  }
  if (typeof value === "object") return Object.values(value as Record<string, unknown>).filter(Boolean).join(" · ") || "—";
  return String(value);
}

/** Earlier deeds with copy fingerprints (journey step 3, "আগের দলিল" tab). */
export function DeedArchive({ landId, items, onOpenSource }: { landId: string; items: DeedArchiveItemOut[]; onOpenSource: (docId: string) => void }) {
  const strings = useStrings();
  const en = useLang() === "en";
  const t = (b: string, e: string) => (en ? e : b);
  const [fingerprints, setFingerprints] = useState<Record<string, FingerprintVerificationOut>>({});
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const verifyCopy = async (documentId: string) => {
    setBusyId(documentId);
    setError(null);
    try {
      const result = await api.verifyDocumentFingerprint(documentId);
      setFingerprints((current) => ({ ...current, [documentId]: result }));
    } catch (e) {
      setError(e instanceof Error ? e.message : strings.deedArchive.noBaseline);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-3">
      <p className="text-sm leading-relaxed text-muted">{strings.deedArchive.description}</p>
      <p className="text-sm font-semibold text-warn">{strings.deedArchive.officialNotice}</p>
      <p className="text-xs leading-relaxed text-muted">{strings.deedArchive.authenticityLimit}</p>
      <div className="flex flex-wrap gap-2">
        <Link href={`/upload/${landId}`} className="inline-flex min-h-11 items-center rounded-lg border border-line px-3 py-2 text-sm font-semibold text-accent">{strings.deedArchive.add}</Link>
        <Link href={`/cases/${landId}/deeds`} className="inline-flex min-h-11 items-center rounded-lg border border-line px-3 py-2 text-sm font-semibold text-accent">{t("বিস্তারিত পাতা", "Full page")} →</Link>
      </div>
      {error && <p role="alert" className="rounded-lg border border-bad/40 bg-bad-bg p-3 text-sm">{error}</p>}
      {items.length ? <ol className="space-y-3">
        {items.map((deed, index) => {
          const check = fingerprints[deed.id];
          const busy = busyId === deed.id;
          return <li key={deed.id} className="min-w-0 rounded-xl border border-line bg-bg/40 p-3 sm:p-4">
            <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0 space-y-1">
                <h4 className="break-words font-semibold">{deed.data?.deed_no ? `${strings.deedArchive.title} · ${deed.data.deed_no}` : deed.original_filename}</h4>
                <p className="break-words text-sm text-muted">{deed.data?.registration_date || deed.data?.registration_date_text || deed.data?.deed_year || "—"} · {(deed.data?.sellers ?? []).map((p) => p.name).join(", ")} → {(deed.data?.buyers ?? []).map((p) => p.name).join(", ")}</p>
                <p className="break-all text-xs text-muted">{strings.deedArchive.uploadedAt}: {new Date(deed.created_at).toLocaleDateString(en ? "en-GB" : "bn-BD")}{deed.uploaded_by ? ` · ${strings.deedArchive.uploadedBy}: ${deed.uploaded_by}` : ""}</p>
              </div>
              <button type="button" aria-haspopup="dialog" onClick={() => onOpenSource(deed.id)} className="min-h-11 shrink-0 rounded-lg border border-line bg-surface px-3 py-2 text-left text-sm font-semibold text-accent">{strings.deedArchive.source}</button>
            </div>
            <p className="mt-2 break-all text-xs text-muted">{strings.deedArchive.fingerprint}: {deed.content_sha256 || strings.deedArchive.noBaseline}</p>
            <button type="button" onClick={() => verifyCopy(deed.id)} disabled={busy} className="mt-2 min-h-11 rounded-lg border border-line bg-surface px-3 py-2 text-sm font-semibold disabled:opacity-60">{busy ? strings.deedArchive.checking : strings.deedArchive.verifyCopy}</button>
            {check && <p role="status" className={`mt-2 text-sm ${check.unchanged_since_upload === false ? "text-bad" : "text-muted"}`}>
              {check.unchanged_since_upload === true ? strings.deedArchive.unchanged : check.unchanged_since_upload === false ? strings.deedArchive.changed : strings.deedArchive.noBaseline}
              <span className="block break-all text-xs">SHA-256: {check.current_sha256}</span>
            </p>}
            {index > 0 && <div className="mt-3 space-y-2 border-t border-line pt-3">
              <h5 className="text-sm font-semibold">{strings.deedArchive.comparison}</h5>
              <div className="space-y-2">{deed.comparison.map((field) => <div key={field.key} className="grid min-w-0 gap-1 rounded-lg bg-surface p-2 text-sm sm:grid-cols-[8rem_1fr_1fr]">
                <strong className="break-words">{field.label_bn}</strong>
                <span className="min-w-0 break-words"><span className="text-xs text-muted">{strings.deedArchive.previousValue}: </span>{archiveValue(field.previous)}</span>
                <span className="min-w-0 break-words"><span className="text-xs text-muted">{strings.deedArchive.currentValue}: </span>{archiveValue(field.current)}</span>
              </div>)}</div>
            </div>}
          </li>;
        })}
      </ol> : <p className="rounded-lg bg-bg p-3 text-sm text-muted">{strings.deedArchive.empty}</p>}
    </div>
  );
}
