"use client";

import { ChangeEvent, useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { api, ApiError, GuardianAlertOut, GuardianLandOut } from "@/lib/api";
import { strings, guardianFlow as copy } from "@/lib/strings";

function value(data: Record<string, unknown>, field: string) {
  if (field === "owners") return Array.isArray(data.owners) ? data.owners.map((o) => (o as { name?: string }).name).join(", ") : "—";
  if (field === "total_area_text") return String(data.total_area_text ?? "—");
  if (field === "mutation_case_ref") return String(data.mutation_case_ref ?? "—");
  if (field === "khatian_no") return String(data.khatian_no ?? "—");
  if (field === "annual_revenue_text") return String(data.annual_revenue_text ?? "—");
  return "—";
}

export function GuardianDashboard() {
  const [lands, setLands] = useState<GuardianLandOut[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [alerts, setAlerts] = useState<GuardianAlertOut[]>([]);
  const [active, setActive] = useState<GuardianAlertOut | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [guide, setGuide] = useState("");

  const refresh = useCallback(async () => {
    try {
      const rows = await api.getGuardianLands();
      setLands(rows);
      if (!selected && rows[0]) setSelected(rows[0].id);
    } catch { setMessage(copy.error); }
  }, [selected]);

  useEffect(() => {
    const timer = window.setTimeout(() => void refresh(), 0);
    return () => window.clearTimeout(timer);
  }, [refresh]);
  useEffect(() => {
    if (!selected) return;
    void api.getGuardianAlerts(selected).then((rows) => { setAlerts(rows); setActive(rows[0] ?? null); }).catch(() => setMessage(copy.error));
  }, [selected]);

  const upload = async (event: ChangeEvent<HTMLInputElement>, land?: GuardianLandOut) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setBusy(true); setMessage(copy.uploadSuccess);
    try {
      const doc = await api.uploadGuardianKhatian(file);
      let ready = doc;
      for (let i = 0; i < 45 && ready.status !== "done"; i++) {
        if (ready.status === "failed") throw new Error(ready.error_message || copy.error);
        await new Promise((resolve) => window.setTimeout(resolve, 1000));
        ready = await api.getDocument(doc.id);
      }
      if (ready.status !== "done") throw new Error(copy.error);
      if (land) await api.checkGuardianLand(land.id, doc.id);
      else await api.addGuardianLand(doc.id);
      await refresh();
      setMessage("");
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : error instanceof Error ? error.message : copy.error);
    } finally { setBusy(false); }
  };

  const monthly = async () => {
    setBusy(true); setMessage("");
    try {
      await api.runGuardianDemo();
      await refresh();
      const rows = selected ? await api.getGuardianAlerts(selected) : [];
      setAlerts(rows); setActive(rows[0] ?? null);
    } catch { setMessage(copy.error); }
    finally { setBusy(false); }
  };

  const showGuide = async () => {
    setBusy(true);
    try { const result = await api.getObjectionGuide(); setGuide(`${result.notice_bn}\n\n${result.text}`); }
    catch { setMessage(copy.error); }
    finally { setBusy(false); }
  };

  const selectedLand = lands.find((land) => land.id === selected);
  const hasDemo = lands.some((land) => land.demo_document_id);
  const statusLabel = (status: GuardianLandOut["status"]) => status === "bad" ? copy.changed : status === "warn" ? copy.review : copy.unchanged;
  const statusStyle = (status: GuardianLandOut["status"]) => status === "bad" ? "border-bad/40 bg-bad/10 text-bad" : status === "warn" ? "border-warn/40 bg-warn/10 text-warn" : "border-ok/40 bg-ok/10 text-ok";

  return (
    <main className="mx-auto max-w-6xl space-y-7 py-2 sm:space-y-9">
      <header className="max-w-3xl border-b border-line pb-6">
        <p className="mb-3 text-sm font-semibold text-accent">জমি কেনার পরে</p>
        <h1 className="text-3xl font-semibold leading-tight text-ink sm:text-4xl">{strings.pages.guardian.title}</h1>
        <p className="mt-3 text-sm leading-7 text-muted">{strings.pages.guardian.desc}</p>
      </header>

      <section className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
        <label className="inline-flex min-h-11 cursor-pointer items-center justify-center rounded-md bg-accent px-5 py-2.5 text-center text-sm font-medium text-white hover:opacity-90">
          {copy.add}<input className="sr-only" type="file" accept="image/*,.pdf" disabled={busy} onChange={(event) => void upload(event)} />
        </label>
        {hasDemo && <Button variant="ghost" disabled={busy} onClick={() => void monthly()}>{busy ? copy.busy : copy.monthly}</Button>}
        <p className="basis-full text-sm leading-6 text-muted">{copy.limits}</p>
      </section>
      {message && <p role="status" className="rounded-md border border-warn/40 bg-warn/10 p-3 text-sm text-ink">{message}</p>}

      {!lands.length && <section className="rounded-xl border border-line bg-surface p-6 text-sm text-muted">{copy.noLands}</section>}
      <div className="grid gap-6 lg:grid-cols-[minmax(270px,0.8fr)_minmax(0,1.4fr)]">
        <section aria-label="নজরদারির জমি" className="space-y-3">
          {lands.map((land) => (
            <article key={land.id} className={`rounded-xl border p-4 ${selected === land.id ? "border-accent/60 bg-surface" : "border-line bg-surface/60"}`}>
              <button className="w-full text-left" onClick={() => setSelected(land.id)} aria-pressed={selected === land.id}>
                <div className="flex flex-wrap items-start justify-between gap-2"><h2 className="font-semibold text-ink">{land.label_bn}</h2><Badge className={statusStyle(land.status)}>{statusLabel(land.status)}</Badge></div>
                <p className="mt-2 text-sm text-muted">{land.district} · {land.upazila} · {land.mouza}</p>
                <p className="mt-1 text-xs text-muted">শেষ যাচাই: {land.last_checked_at ? new Date(land.last_checked_at).toLocaleDateString("bn-BD") : "এখনও হয়নি"}</p>
              </button>
              {land.documents.length > 0 && <div className="mt-3 space-y-1 text-xs text-muted"><p>{copy.documents}</p>{land.documents.map((doc) => <p key={doc.id} className="break-words">{doc.original_filename} · {doc.integrity}</p>)}</div>}
              <label className="mt-3 inline-flex min-h-10 cursor-pointer items-center rounded-md border border-line px-3 py-2 text-sm text-ink hover:bg-surface">
                {copy.upload}<input className="sr-only" type="file" accept="image/*,.pdf" disabled={busy} onChange={(event) => void upload(event, land)} />
              </label>
            </article>
          ))}
        </section>

        <section className="min-w-0 space-y-4">
          {selectedLand && <div className="rounded-xl border border-line bg-surface p-4 sm:p-5">
            <div className="flex flex-wrap items-center justify-between gap-2"><h2 className="text-xl font-semibold text-ink">{selectedLand.label_bn}</h2><Badge className={statusStyle(selectedLand.status)}>{statusLabel(selectedLand.status)}</Badge></div>
            {!active ? <p className="mt-4 text-sm text-muted">{copy.noChanges}</p> : <>
              <div className={`mt-4 rounded-lg border p-4 ${statusStyle(active.severity === "bad" ? "bad" : active.severity === "info" ? "warn" : "warn")}`}>
                <p className="font-semibold">{active.message_bn}</p>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">{active.changes.map((change, i) => <li key={`${change.field}-${i}`}>{change.message_bn}: {String(change.old ?? "—")} → {String(change.new ?? "—")}</li>)}</ul>
              </div>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {([[copy.oldSnapshot, active.old], [copy.newSnapshot, active.new]] as const).map(([title, snapshot]) => <SnapshotCard key={title} title={title} data={snapshot} changes={active.changes} />)}
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <Button size="sm" onClick={() => void api.downloadGuardianCase(active.id)}>{copy.sendLawyer}</Button>
                <Button size="sm" variant="ghost" onClick={() => void showGuide()}>{copy.guide}</Button>
                {!active.read_at && <Button size="sm" variant="ghost" onClick={() => void api.readGuardianAlert(active.id).then(() => refresh())}>পড়া হয়েছে</Button>}
              </div>
              {alerts.length > 1 && <div className="mt-4 flex flex-wrap gap-2">{alerts.map((alert) => <button key={alert.id} onClick={() => setActive(alert)} className="rounded-full border border-line px-3 py-1.5 text-xs text-ink">{new Date(alert.created_at).toLocaleDateString("bn-BD")} · {alert.message_bn}</button>)}</div>}
            </>}
          </div>}
        </section>
      </div>
      {guide && <div role="dialog" aria-modal="true" aria-label={copy.guide} className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-3 sm:items-center"><section className="max-h-[85vh] w-full max-w-3xl overflow-auto rounded-xl bg-surface p-5 shadow-xl sm:p-7"><div className="flex justify-between gap-4"><h2 className="text-xl font-semibold text-ink">{copy.guide}</h2><button className="min-h-11 px-3" onClick={() => setGuide("")}>বন্ধ</button></div><p className="mt-4 rounded bg-warn/10 p-3 text-sm font-semibold text-warn">{copy.verifiedNotice}</p><pre className="mt-4 whitespace-pre-wrap text-sm leading-7 text-ink">{guide}</pre></section></div>}
    </main>
  );
}

function SnapshotCard({ title, data, changes }: { title: string; data: Record<string, unknown>; changes: GuardianAlertOut["changes"] }) {
  const entries = [["owners", "মালিক"], ["khatian_no", "খতিয়ান নম্বর"], ["mutation_case_ref", "নামজারি মামলা"], ["annual_revenue_text", "খাজনা"], ["total_area_text", "মোট জমি"]] as const;
  const changed = new Set(changes.map((change) => change.field));
  return <article className="min-w-0 rounded-lg border border-line p-3 sm:p-4"><h3 className="font-semibold text-ink">{title}</h3><dl className="mt-2 space-y-2">{entries.map(([field, label]) => <div key={field} className={`rounded px-2 py-1.5 ${changed.has(field) || (field === "owners" && changed.has("owners.share")) ? "bg-warn/15" : ""}`}><dt className="text-xs text-muted">{label}</dt><dd className="break-words text-sm text-ink">{value(data, field)}</dd></div>)}</dl></article>;
}
