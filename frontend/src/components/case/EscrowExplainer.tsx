"use client";

import { bnDigits } from "@/lib/digits";
import { useLang, useStrings } from "@/lib/lang";

// How bayna escrow works (was the /escrow page; now journey step 7).
const steps = [
  { title: "চুক্তির শর্ত ঠিক করুন", titleEn: "Set the contract conditions", detail: "বায়না কোন শর্তে ছাড় হবে বা ফেরত যাবে তা চুক্তিতে নির্ধারিত থাকে।", detailEn: "The contract sets when the bayna is released and when it is refunded." },
  { title: "ব্যাংক অংশীদার অর্থ রাখে", titleEn: "A partner bank holds the money", detail: "বায়নার টাকা অংশীদার ব্যাংকের কাছে থাকে; JomiGuard টাকা ধরে না।", detailEn: "The bayna money stays with the partner bank; JomiGuard never holds money." },
  { title: "শর্ত অনুযায়ী নিষ্পত্তি", titleEn: "Settled by the conditions", detail: "চুক্তির শর্ত পূরণ হলে অর্থ ছাড় হয়, অন্যথায় ফেরতের ব্যবস্থা হয়।", detailEn: "If the conditions are met the money is released; otherwise it is refunded." },
];

export function EscrowExplainer() {
  const strings = useStrings();
  const en = useLang() === "en";
  return (
    <div className="space-y-3">
      <ol className="grid gap-3 md:grid-cols-3">
        {steps.map((step, i) => (
          <li key={step.title} className="rounded-[var(--radius-control)] border border-edge bg-bg/60 p-3">
            <p className="font-mono text-xs text-gold">{en ? `0${i + 1}` : bnDigits(`0${i + 1}`)}</p>
            <p className="mt-1 text-sm font-semibold text-ink">{en ? step.titleEn : step.title}</p>
            <p className="mt-1 text-xs leading-5 text-muted">{en ? step.detailEn : step.detail}</p>
          </li>
        ))}
      </ol>
      <p className="border-l-2 border-gold pl-3 text-xs leading-5 text-muted">{strings.pages.escrow.note}</p>
    </div>
  );
}
