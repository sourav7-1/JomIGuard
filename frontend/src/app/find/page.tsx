"use client";

import React, { Suspense, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { api, LandOut } from "@/lib/api";
import { divisionOf, divisions, isListedLand, norm } from "@/lib/bd-locations";
import { Card } from "@/components/ui/Card";
import { Modal } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";
import { services } from "@/lib/services";
import { bnDigits } from "@/lib/digits";

const bn = bnDigits;

// Where "কেস খুলুন" lands for each service (anchors on the case page).
const TARGET: Record<string, string> = { satellite: "#satellite-title", seller: "#seller-identity" };

const field = "w-full min-h-11 rounded-[var(--radius-control)] border border-line bg-bg px-3.5 py-2.5 text-base text-ink disabled:opacity-60";

export default function FindPage() {
  return <Suspense><FindCase /></Suspense>;
}

function FindCase() {
  const serviceId = useSearchParams().get("service") ?? "documents";
  const service = services.find((s) => s.id === serviceId) ?? services[0];

  const [lands, setLands] = useState<LandOut[] | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [division, setDivision] = useState("");
  const [district, setDistrict] = useState("");
  const [upazila, setUpazila] = useState("");
  const [mouza, setMouza] = useState("");
  const [khatian, setKhatian] = useState("");
  const [dag, setDag] = useState("");
  const [creating, setCreating] = useState(false);
  const [busy, setBusy] = useState(false);
  const router = useRouter();
  const toast = useToast();

  useEffect(() => {
    api.getLands().then((rows) => setLands(rows.filter(isListedLand))).catch(() => setLoadError(true));
  }, []);

  // "নতুন কেস" step: confirm the picked address in a modal, then create the case and go to upload.
  const createCase = async () => {
    setBusy(true);
    try {
      const land = await api.createLand({
        district, mouza: mouza.trim(), dag_no: dag.trim(), upazila: upazila.trim(),
        ...(khatian.trim() && { khatian_no: khatian.trim() }),
      });
      toast("ok", "নতুন কেস তৈরি হয়েছে। এবার কাগজ যোগ করুন।");
      router.push(`/upload/${land.id}`);
    } catch (e) {
      toast("bad", e instanceof Error ? e.message : "কেস তৈরি করা যায়নি।");
      setBusy(false);
    }
  };
  const picked: [string, string][] = [["বিভাগ", division], ["জেলা", district], ["উপজেলা", upazila], ["মৌজা", mouza], ["খতিয়ান নং", khatian], ["দাগ নং", dag]];

  const districts = divisions.find((d) => d.name === division)?.districts ?? [];
  // Suggestions come from existing cases only; anything else can be typed.
  const inArea = (l: LandOut) => (!district || !l.district || l.district === district) && (!upazila || !l.upazila || norm(l.upazila) === norm(upazila));
  const upazilaHints = useMemo(() => [...new Set((lands ?? []).filter((l) => l.district === district && l.upazila).map((l) => l.upazila))], [lands, district]);
  const mouzaHints = [...new Set((lands ?? []).filter(inArea).map((l) => l.mouza).filter(Boolean))];

  const matches = !mouza.trim() ? [] : (lands ?? []).filter((l) =>
    inArea(l) && norm(l.mouza) === norm(mouza)
    && (!dag.trim() || norm(l.dag_no) === norm(dag))
    && (!khatian.trim() || !l.khatian_no || norm(l.khatian_no) === norm(khatian)));

  const newCase = "/upload?" + new URLSearchParams(Object.entries({ district, upazila, mouza, dag, khatian }).filter(([, v]) => v.trim())).toString();

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header className="space-y-2">
        <p className="flex items-center gap-3 text-sm font-semibold text-accent"><span className="h-px w-8 bg-gold" />{service.title}</p>
        <h1 className="text-3xl font-semibold tracking-tight text-ink">জমির ঠিকানা দিয়ে কেস খুঁজুন</h1>
        <p className="text-base leading-7 text-muted">বিভাগ থেকে মৌজা পর্যন্ত বেছে নিন। এই মৌজা-দাগে আগের কেস থাকলে সেটি খুলুন, না থাকলে নতুন কেস শুরু করুন।</p>
      </header>

      <form onSubmit={(e) => e.preventDefault()} className="surface-grad grid gap-4 rounded-[var(--radius-card)] border border-edge bg-surface p-5 shadow-raised sm:grid-cols-2 sm:p-6">
        <label className="space-y-1.5"><span className="block text-sm font-semibold text-ink">বিভাগ</span>
          <select className={field} value={division} onChange={(e) => { setDivision(e.target.value); setDistrict(""); setUpazila(""); }}>
            <option value="">বিভাগ বেছে নিন</option>
            {divisions.map((d) => <option key={d.name}>{d.name}</option>)}
          </select>
        </label>
        <label className="space-y-1.5"><span className="block text-sm font-semibold text-ink">জেলা</span>
          <select className={field} value={district} disabled={!division} onChange={(e) => { setDistrict(e.target.value); setUpazila(""); }}>
            <option value="">{division ? "জেলা বেছে নিন" : "আগে বিভাগ বেছে নিন"}</option>
            {districts.map((d) => <option key={d}>{d}</option>)}
          </select>
        </label>
        <label className="space-y-1.5"><span className="block text-sm font-semibold text-ink">উপজেলা</span>
          <input className={field} list="upazila-hints" value={upazila} disabled={!district} onChange={(e) => setUpazila(e.target.value)} placeholder={district ? "লিখুন বা বেছে নিন" : "আগে জেলা বেছে নিন"} />
          <datalist id="upazila-hints">{upazilaHints.map((u) => <option key={u} value={u} />)}</datalist>
        </label>
        <label className="space-y-1.5"><span className="block text-sm font-semibold text-ink">মৌজা <span className="text-bad">*</span></span>
          <input className={field} list="mouza-hints" value={mouza} onChange={(e) => setMouza(e.target.value)} placeholder="লিখুন বা বেছে নিন" required />
          <datalist id="mouza-hints">{mouzaHints.map((m) => <option key={m} value={m} />)}</datalist>
        </label>
        <label className="space-y-1.5"><span className="block text-sm font-semibold text-ink">খতিয়ান নং</span>
          <input className={field} inputMode="numeric" value={khatian} onChange={(e) => setKhatian(e.target.value)} placeholder="যেমন ৩৫২" />
        </label>
        <label className="space-y-1.5"><span className="block text-sm font-semibold text-ink">দাগ নং</span>
          <input className={field} value={dag} onChange={(e) => setDag(e.target.value)} placeholder="যেমন ৪১৭ বা ৩০৫/১" />
        </label>
        <p className="text-xs text-muted sm:col-span-2">বাংলা বা ইংরেজি সংখ্যায় লিখতে পারেন। তালিকায় উপজেলা বা মৌজা না থাকলে নিজে লিখে দিন।</p>
      </form>

      <section aria-live="polite" className="space-y-3">
        {loadError && <p role="alert" className="rounded-lg border border-bad/30 bg-bad-bg p-3 text-sm text-bad">আগের কেসের তালিকা আনা যায়নি। নতুন কেস শুরু করতে পারেন।</p>}
        {!mouza.trim() ? (
          <p className="text-sm text-muted">মৌজা লিখলে এখানে মিলে যাওয়া কেস দেখাবে।</p>
        ) : matches.length ? (
          <>
            <p className="font-semibold text-ok">✓ এই ঠিকানায় {bn(String(matches.length))}টি কেস আছে</p>
            <ul className="grid gap-2">
              {matches.slice(0, 5).map((l) => (
                <Card key={l.id} as="li" variant="interactive" href={`/cases/${l.id}${TARGET[service.id] ?? ""}`} padded={false} className="px-4 py-3"
                  title={<span className="font-body text-base">{l.mouza} · দাগ {bn(l.dag_no || "—")}{l.khatian_no && <> · খতিয়ান {bn(l.khatian_no)}</>}</span>}
                  description={[l.upazila, l.district, divisionOf(l.district ?? "")].filter(Boolean).join(", ")}
                  meta={<span aria-hidden="true" className="text-sm font-semibold text-accent">কেস খুলুন →</span>} />
              ))}
            </ul>
            <p className="text-sm text-muted">অথবা <button type="button" aria-haspopup="dialog" onClick={() => setCreating(true)} className="min-h-11 font-semibold text-accent underline underline-offset-4">নতুন কেস শুরু করুন</button></p>
          </>
        ) : (
          <div className="rounded-[var(--radius-card)] border border-dashed border-line bg-bg p-4">
            <p className="text-sm text-ink">এই ঠিকানায় এখনো কোনো কেস নেই।</p>
            <button type="button" aria-haspopup="dialog" onClick={() => setCreating(true)} className="mt-3 inline-flex min-h-11 items-center rounded-[var(--radius-control)] bg-accent px-4 text-sm font-semibold text-white shadow-rest">নতুন কেস শুরু করুন →</button>
          </div>
        )}
      </section>

      <Modal
        open={creating}
        onClose={() => setCreating(false)}
        title="নতুন কেস শুরু করুন"
        description="বেছে নেওয়া ঠিকানা দেখে নিন। কেস তৈরি হলে কাগজ যোগ করার ধাপে যাবেন।"
        footer={<>
          <Link href={newCase} className="inline-flex min-h-11 items-center rounded-[var(--radius-control)] border border-line bg-surface px-4 text-sm font-semibold text-ink hover:bg-bg">ফর্মে বদলান</Link>
          <button type="button" onClick={createCase} disabled={busy || !district || !mouza.trim()} className="min-h-11 rounded-[var(--radius-control)] bg-accent px-4 text-sm font-semibold text-white shadow-rest">{busy ? "তৈরি হচ্ছে…" : "কেস তৈরি করুন →"}</button>
        </>}
      >
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
          {picked.map(([k, v]) => <React.Fragment key={k}><dt className="text-muted">{k}</dt><dd className="font-semibold text-ink">{v.trim() ? bn(v) : "—"}</dd></React.Fragment>)}
        </dl>
        {!district && <p role="alert" className="mt-4 rounded-[var(--radius-control)] bg-warn-bg p-3 text-sm text-warn">কেস তৈরির আগে বিভাগ ও জেলা বেছে নিন।</p>}
      </Modal>
    </div>
  );
}
