"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, EscrowOut } from "@/lib/api";
import { escrowFlow as s } from "@/lib/strings";
import { Card } from "@/components/ui/Card";
import { ListSkeleton } from "@/components/ui/Skeleton";
import { useConfirm } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";

const money = (paisa: number) => {
  const amount = BigInt(paisa);
  const hundred = BigInt(100);
  const absolute = amount < BigInt(0) ? -amount : amount;
  const sign = amount < BigInt(0) ? "−" : "";
  const cents = (absolute % hundred).toString().padStart(2, "0").replace(/\d/g, (d) => "০১২৩৪৫৬৭৮৯"[Number(d)]);
  return `${sign}৳${(absolute / hundred).toLocaleString("bn-BD")}.${cents}`;
};

export default function EscrowDealClient({ id }: { id: string }) {
  const [deal, setDeal] = useState<EscrowOut | null>(null);
  const [deed, setDeed] = useState("");
  const [registrationDate, setRegistrationDate] = useState(new Date().toISOString().slice(0, 10));
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const { ask, dialog } = useConfirm();
  const toast = useToast();
  const refresh = useCallback(async () => { try { setDeal(await (id === "demo-00026" ? api.getDemoEscrow("00026") : api.getEscrow(id))); } catch { setError(s.error); } }, [id]);
  useEffect(() => {
    // Fetches the initial server state after the dynamic route id is available.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refresh();
  }, [refresh]);
  const act = async (fn: () => Promise<EscrowOut>) => {
    setBusy(true); setError("");
    try { const next = await fn(); setDeal(next); toast("ok", `${s.state}: ${s.states[next.state as keyof typeof s.states] || next.state}`); }
    catch (e) { const msg = e instanceof Error ? e.message : s.error; setError(msg); toast("bad", msg); }
    finally { setBusy(false); }
  };
  // Irreversible steps ask first (no browser confirm()).
  const confirmAct = async (title: string, message: string, label: string, fn: () => Promise<EscrowOut>, danger = false) => {
    if (await ask({ title, message, confirmLabel: label, danger })) await act(fn);
  };
  if (!deal) return <main className="mx-auto max-w-4xl space-y-4 p-4 sm:py-8">{error ? <p role="alert" className="rounded-lg bg-bad-bg p-3 text-sm">{error}</p> : <ListSkeleton rows={3} className="grid gap-3 sm:grid-cols-3" />}</main>;
  const step = deal.state === "refunded" ? 4 : ["draft", "agreed", "funded", "conditions_met", "registered", "released"].indexOf(deal.state);
  return <main className="mx-auto max-w-4xl space-y-6 p-4 sm:py-8">
    <header className="space-y-2"><Link href={`/cases/${deal.land_id}`} className="text-sm text-accent underline">{s.back}</Link><h1 className="font-heading text-2xl font-bold">{s.title}</h1><p className="text-sm text-muted">{s.state}: {s.states[deal.state as keyof typeof s.states] || deal.state}</p></header>
    {dialog}
    <ol aria-label={s.steps.join(", ")} className="grid grid-cols-2 gap-2 sm:grid-cols-5">{s.steps.map((label, i) => <Card as="li" key={label} padded={false} aria-current={i === step ? "step" : undefined} className={`flex items-center gap-2 p-3 text-sm ${i <= step ? "!border-accent/40 !bg-accent-soft font-semibold" : "text-muted"}`}><span className={`inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold ${i < step ? "bg-ok text-surface" : i === step ? "animate-pulse-ring bg-accent text-surface" : "border border-line bg-surface"}`}>{i < step ? "✓" : "১২৩৪৫৬"[i]}</span>{label}</Card>)}</ol>
    <section className="grid grid-cols-1 gap-3 sm:grid-cols-3">{s.purses.map((label, i) => <Card as="article" key={label} variant={i === 1 ? "highlight" : "default"} tone="info" className={i === 1 ? "!border-l-accent" : ""}><p className="text-sm text-muted">{label}</p><strong className="mt-1 block text-xl">{money([deal.balances.buyer_paisa, deal.balances.escrow_paisa, deal.balances.seller_paisa][i])}</strong></Card>)}</section>
    <p className="rounded-xl border border-warn/40 bg-warn-bg p-3 text-sm">{s.mock}</p>
    <Card as="section" title={s.conditions} titleAs="h2">{deal.conditions.map(c => <Card as="article" key={c.id} variant="highlight" tone={c.met ? "ok" : "info"} className="!p-3 !shadow-none"><p className="font-medium">{c.met ? "✓" : "○"} {c.label_bn}</p><p className="mt-1 text-sm text-muted">{c.detail_bn}</p></Card>)}</Card>
    <div className="flex flex-wrap gap-2">
      {!deal.buyer_agreed && <button disabled={busy} onClick={() => act(() => api.agreeEscrow(deal.id))} className="min-h-11 rounded-lg bg-accent px-4 text-white">{s.agree}</button>}
      {["draft", "agreed"].includes(deal.state) && <button disabled={busy} onClick={() => confirmAct("চুক্তি বাতিল করবেন?", "বাতিল করলে এই escrow চুক্তি আর এগোবে না; আবার শুরু করতে নতুন চুক্তি লাগবে।", s.cancel, () => api.cancelEscrow(deal.id), true)} className="min-h-11 rounded-lg border border-line px-4">{s.cancel}</button>}
      {deal.state === "agreed" && <button disabled={busy} onClick={() => act(() => api.depositEscrow(deal.id))} className="min-h-11 rounded-lg bg-accent px-4 text-white">{s.deposit}</button>}
      {["funded", "conditions_met"].includes(deal.state) && <button disabled={busy} onClick={() => act(() => api.checkEscrow(deal.id))} className="min-h-11 rounded-lg border border-line px-4">{s.check}</button>}
      {deal.state === "conditions_met" && <div className="flex flex-wrap gap-2"><input aria-label={s.deedNo} value={deed} onChange={e => setDeed(e.target.value)} placeholder={s.deedNo} className="min-h-11 min-w-0 rounded-lg border border-line bg-surface px-3"/><label className="flex min-h-11 items-center gap-2 rounded-lg border border-line px-3 text-sm"><span>{s.registrationDate}</span><input aria-label={s.registrationDate} type="date" value={registrationDate} onChange={e => setRegistrationDate(e.target.value)} className="min-h-9 bg-surface"/></label><button disabled={busy || !deed.trim() || !registrationDate} onClick={() => act(() => api.registerEscrow(deal.id, deed, registrationDate))} className="min-h-11 rounded-lg bg-accent px-4 text-white">{s.record}</button></div>}
      {deal.state === "registered" && <button disabled={busy} onClick={() => confirmAct("বিক্রেতাকে টাকা ছাড়বেন?", "ছাড় দিলে escrow-র বায়নার টাকা বিক্রেতার হিসাবে যাবে (ডেমোতে নমুনা ব্যাংক)। এই ধাপ ফেরানো যায় না।", s.release, () => api.releaseEscrow(deal.id))} className="min-h-11 rounded-lg bg-accent px-4 text-white">{s.release}</button>}
      {["funded", "conditions_met"].includes(deal.state) && <button disabled={busy} onClick={() => confirmAct("সময়সীমা পেরিয়েছে ধরে নেবেন?", "এতে চুক্তি ফেরতের দিকে যাবে: বায়নার টাকা ক্রেতার কাছে ফেরত যাবে (ডেমোতে নমুনা ব্যাংক)। এই ধাপ ফেরানো যায় না।", s.expire, () => api.expireEscrow(deal.id), true)} className="min-h-11 rounded-lg border border-warn text-warn px-4">{s.expire}</button>}
      <button onClick={() => api.downloadBaynanama(deal.id).catch(e => setError(e.message))} className="min-h-11 rounded-lg border border-line px-4">{s.pdf}</button>
    </div>
    {error && <p role="alert" className="rounded-lg bg-bad-bg p-3 text-sm">{error}</p>}
    <section className="space-y-2"><h2 className="font-heading text-lg font-bold">{s.events}</h2>{deal.events.map((event, i) => <article key={`${event.created_at}-${i}`} className="rounded-[var(--radius-control)] border border-edge bg-surface p-3 shadow-rest"><p className="font-semibold">{s.eventNames[event.event as keyof typeof s.eventNames] || event.event} · {s.states[event.from_state as keyof typeof s.states] || event.from_state} → {s.states[event.to_state as keyof typeof s.states] || event.to_state}</p><p className="text-sm text-muted">{event.message_bn}</p></article>)}</section>
    <p className="rounded-xl border border-warn/40 p-3 text-sm">{s.draft}</p>
  </main>;
}
