"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, EscrowOut } from "@/lib/api";
import { escrowFlow as s } from "@/lib/strings";

const money = (paisa: number) => {
  const amount = BigInt(paisa);
  const hundred = BigInt(100);
  const absolute = amount < BigInt(0) ? -amount : amount;
  const sign = amount < BigInt(0) ? "−" : "";
  return `${sign}৳${(absolute / hundred).toLocaleString("bn-BD")}.${(absolute % hundred).toString().padStart(2, "0")}`;
};

export default function EscrowDealClient({ id }: { id: string }) {
  const [deal, setDeal] = useState<EscrowOut | null>(null);
  const [deed, setDeed] = useState("");
  const [registrationDate, setRegistrationDate] = useState(new Date().toISOString().slice(0, 10));
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const refresh = useCallback(async () => { try { setDeal(await (id === "demo-00026" ? api.getDemoEscrow("00026") : api.getEscrow(id))); } catch { setError(s.error); } }, [id]);
  useEffect(() => {
    // Fetches the initial server state after the dynamic route id is available.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refresh();
  }, [refresh]);
  const act = async (fn: () => Promise<EscrowOut>) => { setBusy(true); setError(""); try { setDeal(await fn()); } catch (e) { setError(e instanceof Error ? e.message : s.error); } finally { setBusy(false); } };
  if (!deal) return <main className="mx-auto max-w-3xl p-6" role="status">{error || s.loading}</main>;
  const step = deal.state === "refunded" ? 4 : ["draft", "agreed", "funded", "conditions_met", "registered", "released"].indexOf(deal.state);
  return <main className="mx-auto max-w-4xl space-y-6 p-4 sm:py-8">
    <header className="space-y-2"><Link href={`/cases/${deal.land_id}`} className="text-sm text-accent underline">{s.back}</Link><h1 className="font-heading text-2xl font-bold">{s.title}</h1><p className="text-sm text-muted">{s.state}: {s.states[deal.state as keyof typeof s.states] || deal.state}</p></header>
    <ol aria-label={s.steps.join(", ")} className="grid grid-cols-2 gap-2 sm:grid-cols-5">{s.steps.map((label, i) => <li key={label} className={`rounded-xl border p-3 text-sm ${i <= step ? "border-accent bg-accent/10 font-semibold" : "border-line text-muted"}`}><span className="mr-2">{i + 1}</span>{label}</li>)}</ol>
    <section className="grid grid-cols-1 gap-3 sm:grid-cols-3">{s.purses.map((label, i) => <article key={label} className="rounded-xl border border-line bg-surface p-4"><p className="text-sm text-muted">{label}</p><strong className="mt-1 block text-xl">{money([deal.balances.buyer_paisa, deal.balances.escrow_paisa, deal.balances.seller_paisa][i])}</strong></article>)}</section>
    <p className="rounded-xl border border-warn/40 bg-warn-bg p-3 text-sm">{s.mock}</p>
    <section className="space-y-3 rounded-xl border border-line bg-surface p-4"><h2 className="font-heading text-lg font-bold">{s.conditions}</h2>{deal.conditions.map(c => <article key={c.id} className="rounded-lg border border-line p-3"><p>{c.met ? "✓" : "○"} {c.label_bn}</p><p className="mt-1 text-sm text-muted">{c.detail_bn}</p></article>)}</section>
    <div className="flex flex-wrap gap-2">
      {!deal.buyer_agreed && <button disabled={busy} onClick={() => act(() => api.agreeEscrow(deal.id))} className="min-h-11 rounded-lg bg-accent px-4 text-white">{s.agree}</button>}
      {["draft", "agreed"].includes(deal.state) && <button disabled={busy} onClick={() => act(() => api.cancelEscrow(deal.id))} className="min-h-11 rounded-lg border border-line px-4">{s.cancel}</button>}
      {deal.state === "agreed" && <button disabled={busy} onClick={() => act(() => api.depositEscrow(deal.id))} className="min-h-11 rounded-lg bg-accent px-4 text-white">{s.deposit}</button>}
      {["funded", "conditions_met"].includes(deal.state) && <button disabled={busy} onClick={() => act(() => api.checkEscrow(deal.id))} className="min-h-11 rounded-lg border border-line px-4">{s.check}</button>}
      {deal.state === "conditions_met" && <div className="flex flex-wrap gap-2"><input aria-label={s.deedNo} value={deed} onChange={e => setDeed(e.target.value)} placeholder={s.deedNo} className="min-h-11 min-w-0 rounded-lg border border-line bg-surface px-3"/><label className="flex min-h-11 items-center gap-2 rounded-lg border border-line px-3 text-sm"><span>{s.registrationDate}</span><input aria-label={s.registrationDate} type="date" value={registrationDate} onChange={e => setRegistrationDate(e.target.value)} className="min-h-9 bg-surface"/></label><button disabled={busy || !deed.trim() || !registrationDate} onClick={() => act(() => api.registerEscrow(deal.id, deed, registrationDate))} className="min-h-11 rounded-lg bg-accent px-4 text-white">{s.record}</button></div>}
      {deal.state === "registered" && <button disabled={busy} onClick={() => act(() => api.releaseEscrow(deal.id))} className="min-h-11 rounded-lg bg-accent px-4 text-white">{s.release}</button>}
      {["funded", "conditions_met"].includes(deal.state) && <button disabled={busy} onClick={() => act(() => api.expireEscrow(deal.id))} className="min-h-11 rounded-lg border border-warn text-warn px-4">{s.expire}</button>}
      <button onClick={() => api.downloadBaynanama(deal.id).catch(e => setError(e.message))} className="min-h-11 rounded-lg border border-line px-4">{s.pdf}</button>
    </div>
    {error && <p role="alert" className="rounded-lg bg-bad-bg p-3 text-sm">{error}</p>}
    <section className="space-y-2"><h2 className="font-heading text-lg font-bold">{s.events}</h2>{deal.events.map((event, i) => <article key={`${event.created_at}-${i}`} className="rounded-xl border border-line p-3"><p className="font-semibold">{s.eventNames[event.event as keyof typeof s.eventNames] || event.event} · {s.states[event.from_state as keyof typeof s.states] || event.from_state} → {s.states[event.to_state as keyof typeof s.states] || event.to_state}</p><p className="text-sm text-muted">{event.message_bn}</p></article>)}</section>
    <p className="rounded-xl border border-warn/40 p-3 text-sm">{s.draft}</p>
  </main>;
}
