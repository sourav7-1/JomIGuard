"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { BHOLA_CASE } from "@/lib/services";
import { En } from "@/components/ui/En";
import { bnDigits } from "@/lib/digits";

// Step-by-step judge tour. Spotlight + docked tooltip inside a native <dialog> (focus trap, Esc).
// Steps on a case page use the case the tour was started for (Bhola by default).
type Step = { path: string | "case"; sel: string; title: string; en: string; body: string; bodyEn: string };

const STEPS: Step[] = [
  { path: "/", sel: '[aria-labelledby="services-title"]', title: "সেবাসমূহ", en: "Services",
    body: "ছয়টি সেবা: কাগজ যাচাই, মালিকানার ইতিহাস, স্যাটেলাইট যাচাই, বায়না এসক্রো, প্রবাসী গার্ডিয়ান ও বিক্রেতা যাচাই। প্রতিটি কার্ডে “কীভাবে?” চাপলে ধাপগুলো দেখবেন।",
    bodyEn: "Six services. “কীভাবে?” on each card shows how to use it." },
  { path: "/", sel: '[data-tour="bhola"]', title: "ভোলার নমুনা কেস", en: "The Bhola sample case",
    body: "চর মেঘনার এই প্লটে খতিয়ানে জমি 'নাল', কিন্তু স্যাটেলাইট ছবিতে আশেপাশে পানি বাড়ছে। “পরের ধাপ” চাপলে কেসটি খুলবে।",
    bodyEn: "Paper says farmland, satellite shows rising water. Next opens the case." },
  { path: "case", sel: '[aria-labelledby="tracker-title"]', title: "যাচাইয়ের অবস্থা", en: "Case tracker",
    body: "কাগজ জমা থেকে রিপোর্ট পর্যন্ত ৫টি ধাপ: কাগজ জমা, তথ্য পড়া, মিলিয়ে দেখা, স্যাটেলাইট যাচাই, রিপোর্ট। কোনটা শেষ আর কোনটা বাকি, এখানে দেখা যায়।",
    bodyEn: "Five steps from papers to report, with what is done and what is left." },
  { path: "case", sel: '[data-tour="findings"]', title: "ঝুঁকির মাত্রা ও “যা মেলেনি”", en: "Risk level and mismatches",
    body: "উপরে ঝুঁকির মাত্রা, নিচে প্রতিটি অমিল। অমিলের নিচের উৎস-বোতাম চাপলে নথির যে ঘর থেকে তথ্যটি এসেছে, সেটি চিহ্নিত অবস্থায় খোলে।",
    bodyEn: "Each mismatch opens the exact field of the source document." },
  { path: "case", sel: '[aria-labelledby="satellite-title"]', title: "স্যাটেলাইট যাচাই", en: "Satellite check",
    body: "মানচিত্রে প্লটের সীমানা, প্রতি ফেব্রুয়ারির পানি ও গাছের চার্ট, আর তা থেকে পাওয়া ফল। ফল প্লটের চারপাশের প্রায় ২০০ মিটার এলাকার, প্লটের ভেতরের নয়।",
    bodyEn: "Map, February water and tree charts, and findings for ~200 m around the plot." },
  { path: "case", sel: '[data-tour="next"]', title: "এখন কী করবেন ও PDF রিপোর্ট", en: "Next steps and PDF report",
    body: "অমিল থেকে পাওয়া পরের কাজগুলো, সবচেয়ে জরুরিটা আগে। ঝুঁকির কার্ডের নিচে “PDF রিপোর্ট” বোতামে পুরো ফল নামানো যায়।",
    bodyEn: "Next actions from the findings, most urgent first. “PDF রিপোর্ট” downloads the report." },
  { path: "/demo", sel: "main h1", title: "নিজে চেষ্টা করুন", en: "Try it yourself",
    body: "নমুনা ডেটা পাতায় নথির প্যাক, এক ক্লিকে নতুন কেস আর স্যাটেলাইট নমুনা প্লট আছে। সব নথি কৃত্রিম; আসল কারো নয়।",
    bodyEn: "Demo data: document packs, one-click cases and satellite sample plots. All synthetic." },
];

const SEEN = "jg-tour-seen";
const store = { get: (k: string) => { try { return localStorage.getItem(k); } catch { return null; } },
  set: (k: string, v: string) => { try { localStorage.setItem(k, v); } catch { /* private mode */ } } };

/** Start the tour from anywhere: startTour(), or startTour(3, "/cases/<id>") to begin at the findings. */
export const startTour = (step = 0, casePath?: string) =>
  window.dispatchEvent(new CustomEvent("jomiguard:tour", { detail: { step, casePath } }));

const bnNum = bnDigits;

export function GuidedTour() {
  const pathname = usePathname();
  const router = useRouter();
  const [run, setRun] = useState<{ step: number; casePath: string } | null>(null);
  const [rect, setRect] = useState<DOMRect | null>(null);
  const ref = useRef<HTMLDialogElement>(null);
  const nextRef = useRef<HTMLButtonElement>(null);
  const titleId = useId();
  const bodyId = useId();

  const step = run ? STEPS[run.step] : null;
  const path = step ? (step.path === "case" ? run!.casePath : step.path) : null;

  const close = useCallback(() => { store.set(SEEN, "1"); setRun(null); setRect(null); }, []);
  const go = (i: number) => (i >= STEPS.length ? close() : setRun((r) => r && { ...r, step: Math.max(0, i) }));

  // Start requests (banner, help button, demo one-click).
  useEffect(() => {
    const onStart = (e: Event) => {
      const d = (e as CustomEvent<{ step?: number; casePath?: string }>).detail ?? {};
      setRun({ step: d.step ?? 0, casePath: d.casePath ?? BHOLA_CASE });
    };
    window.addEventListener("jomiguard:tour", onStart);
    return () => window.removeEventListener("jomiguard:tour", onStart);
  }, []);

  // First visit after login: start on the home page once the services are on screen.
  useEffect(() => {
    if (pathname !== "/" || store.get(SEEN) || run) return;
    const t = window.setInterval(() => {
      if (document.querySelector(STEPS[0].sel)) { window.clearInterval(t); setRun({ step: 0, casePath: BHOLA_CASE }); }
    }, 400);
    const stop = window.setTimeout(() => window.clearInterval(t), 20000);
    return () => { window.clearInterval(t); window.clearTimeout(stop); };
  }, [pathname, run]);

  // Open/close the dialog.
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (run && !d.open) d.showModal();
    if (!run && d.open) d.close();
  }, [run]);

  // Go to the step's page, wait for its target, scroll it into view and follow it.
  useEffect(() => {
    if (!step || !path) return;
    if (pathname !== path.split("#")[0]) { router.push(path); return; }
    let el: Element | null = null;
    let raf = 0;
    const started = Date.now();
    const follow = () => {
      if (!el || !el.isConnected) el = document.querySelector(step.sel);
      if (el) {
        const r = el.getBoundingClientRect();
        setRect((old) => (old && old.top === r.top && old.height === r.height && old.width === r.width ? old : r));
      } else if (Date.now() - started > 12000) setRect(null);
      raf = requestAnimationFrame(follow);
    };
    const place = window.setInterval(() => {
      const target = document.querySelector(step.sel);
      if (!target) return;
      window.clearInterval(place);
      const r = target.getBoundingClientRect();
      const room = window.innerHeight - 340; // header on top, tooltip at the bottom
      window.scrollTo({ top: window.scrollY + r.top - (r.height < room ? Math.max(150, (room - r.height) / 2 + 120) : 150), behavior: "smooth" });
    }, 250);
    raf = requestAnimationFrame(follow);
    nextRef.current?.focus();
    return () => { cancelAnimationFrame(raf); window.clearInterval(place); };
  }, [step, path, pathname, router]);

  const pad = 8;
  const spot = rect && path && pathname === path.split("#")[0] ? rect : null;
  return (
    <dialog ref={ref} className="tour" aria-labelledby={titleId} aria-describedby={bodyId}
      onCancel={(e) => { e.preventDefault(); close(); }}
      onWheel={(e) => window.scrollBy(0, e.deltaY)}>
      {step && run && <>
        {spot
          ? <div aria-hidden="true" className="tour-spot" style={{ top: spot.top - pad, left: spot.left - pad, width: spot.width + pad * 2, height: spot.height + pad * 2 }} />
          : <div aria-hidden="true" className="fixed inset-0 bg-[rgb(12_15_32/0.55)]" />}
        <section className="tour-tip animate-fade-up rounded-[var(--radius-card)] border border-edge bg-surface p-4 text-ink shadow-overlay sm:p-5">
          <p className="text-xs font-semibold text-accent">ধাপ {bnNum(run.step + 1)} / {bnNum(STEPS.length)} <span lang="en" className="font-normal text-muted">· Step {run.step + 1} of {STEPS.length}</span></p>
          <h2 id={titleId} className="mt-1 font-heading text-lg font-bold leading-snug">{step.title}<En className="text-muted">{step.en}</En></h2>
          <div id={bodyId} className="mt-2 space-y-1">
            <p className="text-sm leading-6">{step.body}</p>
            <p lang="en" className="text-xs leading-5 text-muted">{step.bodyEn}</p>
            {!spot && <p role="status" className="text-xs text-muted">পাতাটি লোড হচ্ছে… <span lang="en">Loading the page…</span></p>}
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <button type="button" onClick={close} className="min-h-11 rounded-[var(--radius-control)] px-3 text-sm font-semibold text-muted hover:bg-bg">বাদ দিন<En>Skip</En></button>
            <span className="flex-1" />
            {run.step > 0 && <button type="button" onClick={() => go(run.step - 1)} className="min-h-11 rounded-[var(--radius-control)] border border-line bg-surface px-3 text-sm font-semibold hover:bg-bg">← আগের<En>Back</En></button>}
            <button ref={nextRef} type="button" onClick={() => go(run.step + 1)} className="min-h-11 rounded-[var(--radius-control)] bg-accent px-4 text-sm font-semibold text-white shadow-rest">
              {run.step === STEPS.length - 1 ? "শেষ" : "পরের ধাপ →"}<En>{run.step === STEPS.length - 1 ? "Finish" : "Next"}</En>
            </button>
          </div>
        </section>
      </>}
    </dialog>
  );
}
