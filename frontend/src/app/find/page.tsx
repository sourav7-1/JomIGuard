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
import { useLang } from "@/lib/lang";


// Where "কেস খুলুন" lands for each service (anchors on the case page).
const TARGET: Record<string, string> = { satellite: "#satellite-title", seller: "#seller-identity" };

const field = "w-full min-h-11 rounded-[var(--radius-control)] border border-line bg-bg px-3.5 py-2.5 text-base text-ink disabled:opacity-60";

export default function FindPage() {
  return <Suspense><FindCase /></Suspense>;
}

function FindCase() {
  const en = useLang() === "en";
  const t = (b: string, e: string) => (en ? e : b);
  const bn = (v: string) => (en ? v : bnDigits(v));
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
      toast("ok", t("নতুন কেস তৈরি হয়েছে। এবার কাগজ যোগ করুন।", "New case created. Now add papers."));
      router.push(`/upload/${land.id}`);
    } catch (e) {
      toast("bad", e instanceof Error ? e.message : t("কেস তৈরি করা যায়নি।", "Could not create the case."));
      setBusy(false);
    }
  };
  const picked: [string, string][] = [[t("বিভাগ", "Division"), division], [t("জেলা", "District"), district], [t("উপজেলা", "Upazila"), upazila], [t("মৌজা", "Mouza"), mouza], [t("খতিয়ান নং", "Khatian no."), khatian], [t("দাগ নং", "Dag no."), dag]];

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
        <p className="flex items-center gap-3 text-sm font-semibold text-accent"><span className="h-px w-8 bg-gold" />{en ? service.titleEn : service.title}</p>
        <h1 className="text-3xl font-semibold tracking-tight text-ink">{t("জমির ঠিকানা দিয়ে কেস খুঁজুন", "Find a case by land address")}</h1>
        <p className="text-base leading-7 text-muted">{t("বিভাগ থেকে মৌজা পর্যন্ত বেছে নিন। এই মৌজা-দাগে আগের কেস থাকলে সেটি খুলুন, না থাকলে নতুন কেস শুরু করুন।", "Pick everything from division down to mouza. If a case already exists for this mouza and dag, open it; otherwise start a new case.")}</p>
      </header>

      <form onSubmit={(e) => e.preventDefault()} className="surface-grad grid gap-4 rounded-[var(--radius-card)] border border-edge bg-surface p-5 shadow-raised sm:grid-cols-2 sm:p-6">
        <label className="space-y-1.5"><span className="block text-sm font-semibold text-ink">{t("বিভাগ", "Division")}</span>
          <select className={field} value={division} onChange={(e) => { setDivision(e.target.value); setDistrict(""); setUpazila(""); }}>
            <option value="">{t("বিভাগ বেছে নিন", "Choose a division")}</option>
            {divisions.map((d) => <option key={d.name}>{d.name}</option>)}
          </select>
        </label>
        <label className="space-y-1.5"><span className="block text-sm font-semibold text-ink">{t("জেলা", "District")}</span>
          <select className={field} value={district} disabled={!division} onChange={(e) => { setDistrict(e.target.value); setUpazila(""); }}>
            <option value="">{division ? t("জেলা বেছে নিন", "Choose a district") : t("আগে বিভাগ বেছে নিন", "Choose a division first")}</option>
            {districts.map((d) => <option key={d}>{d}</option>)}
          </select>
        </label>
        <label className="space-y-1.5"><span className="block text-sm font-semibold text-ink">{t("উপজেলা", "Upazila")}</span>
          <input className={field} list="upazila-hints" value={upazila} disabled={!district} onChange={(e) => setUpazila(e.target.value)} placeholder={district ? t("লিখুন বা বেছে নিন", "Type or choose") : t("আগে জেলা বেছে নিন", "Choose a district first")} />
          <datalist id="upazila-hints">{upazilaHints.map((u) => <option key={u} value={u} />)}</datalist>
        </label>
        <label className="space-y-1.5"><span className="block text-sm font-semibold text-ink">{t("মৌজা", "Mouza")} <span className="text-bad">*</span></span>
          <input className={field} list="mouza-hints" value={mouza} onChange={(e) => setMouza(e.target.value)} placeholder={t("লিখুন বা বেছে নিন", "Type or choose")} required />
          <datalist id="mouza-hints">{mouzaHints.map((m) => <option key={m} value={m} />)}</datalist>
        </label>
        <label className="space-y-1.5"><span className="block text-sm font-semibold text-ink">{t("খতিয়ান নং", "Khatian no.")}</span>
          <input className={field} inputMode="numeric" value={khatian} onChange={(e) => setKhatian(e.target.value)} placeholder={t("যেমন ৩৫২", "e.g. 352")} />
        </label>
        <label className="space-y-1.5"><span className="block text-sm font-semibold text-ink">{t("দাগ নং", "Dag no.")}</span>
          <input className={field} value={dag} onChange={(e) => setDag(e.target.value)} placeholder={t("যেমন ৪১৭ বা ৩০৫/১", "e.g. 417 or 305/1")} />
        </label>
        <p className="text-xs text-muted sm:col-span-2">{t("বাংলা বা ইংরেজি সংখ্যায় লিখতে পারেন। তালিকায় উপজেলা বা মৌজা না থাকলে নিজে লিখে দিন।", "Bangla or English digits both work. If the upazila or mouza is not in the list, type it in.")}</p>
      </form>

      <section aria-live="polite" className="space-y-3">
        {loadError && <p role="alert" className="rounded-lg border border-bad/30 bg-bad-bg p-3 text-sm text-bad">{t("আগের কেসের তালিকা আনা যায়নি। নতুন কেস শুরু করতে পারেন।", "Could not load existing cases. You can start a new case.")}</p>}
        {!mouza.trim() ? (
          <p className="text-sm text-muted">{t("মৌজা লিখলে এখানে মিলে যাওয়া কেস দেখাবে।", "Type a mouza to see matching cases here.")}</p>
        ) : matches.length ? (
          <>
            <p className="font-semibold text-ok">✓ {en ? `${matches.length} case(s) at this address` : `এই ঠিকানায় ${bn(String(matches.length))}টি কেস আছে`}</p>
            <ul className="grid gap-2">
              {matches.slice(0, 5).map((l) => (
                <Card key={l.id} as="li" variant="interactive" href={`/cases/${l.id}${TARGET[service.id] ?? ""}`} padded={false} className="px-4 py-3"
                  title={<span className="font-body text-base">{l.mouza} · {t("দাগ", "Dag")} {bn(l.dag_no || "—")}{l.khatian_no && <> · {t("খতিয়ান", "Khatian")} {bn(l.khatian_no)}</>}</span>}
                  description={[l.upazila, l.district, divisionOf(l.district ?? "")].filter(Boolean).join(", ")}
                  meta={<span aria-hidden="true" className="text-sm font-semibold text-accent">{t("কেস খুলুন →", "Open case →")}</span>} />
              ))}
            </ul>
            <p className="text-sm text-muted">{t("অথবা", "Or")} <button type="button" aria-haspopup="dialog" onClick={() => setCreating(true)} className="min-h-11 font-semibold text-accent underline underline-offset-4">{t("নতুন কেস শুরু করুন", "Start a new case")}</button></p>
          </>
        ) : (
          <div className="rounded-[var(--radius-card)] border border-dashed border-line bg-bg p-4">
            <p className="text-sm text-ink">{t("এই ঠিকানায় এখনো কোনো কেস নেই।", "No case at this address yet.")}</p>
            <button type="button" aria-haspopup="dialog" onClick={() => setCreating(true)} className="mt-3 inline-flex min-h-11 items-center rounded-[var(--radius-control)] bg-accent px-4 text-sm font-semibold text-white shadow-rest">{t("নতুন কেস শুরু করুন", "Start a new case")} →</button>
          </div>
        )}
      </section>

      <Modal
        open={creating}
        onClose={() => setCreating(false)}
        title={t("নতুন কেস শুরু করুন", "Start a new case")}
        description={t("বেছে নেওয়া ঠিকানা দেখে নিন। কেস তৈরি হলে কাগজ যোগ করার ধাপে যাবেন।", "Check the chosen address. Once the case is created you go to adding papers.")}
        footer={<>
          <Link href={newCase} className="inline-flex min-h-11 items-center rounded-[var(--radius-control)] border border-line bg-surface px-4 text-sm font-semibold text-ink hover:bg-bg">{t("ফর্মে বদলান", "Edit in form")}</Link>
          <button type="button" onClick={createCase} disabled={busy || !district || !mouza.trim()} className="min-h-11 rounded-[var(--radius-control)] bg-accent px-4 text-sm font-semibold text-white shadow-rest">{busy ? t("তৈরি হচ্ছে…", "Creating…") : t("কেস তৈরি করুন →", "Create case →")}</button>
        </>}
      >
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
          {picked.map(([k, v]) => <React.Fragment key={k}><dt className="text-muted">{k}</dt><dd className="font-semibold text-ink">{v.trim() ? bn(v) : "—"}</dd></React.Fragment>)}
        </dl>
        {!district && <p role="alert" className="mt-4 rounded-[var(--radius-control)] bg-warn-bg p-3 text-sm text-warn">{t("কেস তৈরির আগে বিভাগ ও জেলা বেছে নিন।", "Choose a division and district before creating the case.")}</p>}
      </Modal>
    </div>
  );
}
