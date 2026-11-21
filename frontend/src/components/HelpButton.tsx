"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Modal } from "@/components/ui/Modal";
import { En } from "@/components/ui/En";
import { startTour } from "@/components/GuidedTour";

// Floating "?" on every page: a short guide for the page you are on.
type Guide = { title: string; en: string; points: [string, string][] };

const GUIDES: [(p: string) => boolean, Guide][] = [
  [(p) => p === "/", { title: "মূল পাতা", en: "Home", points: [
    ["সেবাসমূহ থেকে একটি সেবা বেছে নিন; “কীভাবে?” চাপলে ধাপ দেখাবে।", "Pick a service; “কীভাবে?” shows its steps."],
    ["নমুনা কেসগুলো খুলে ফলাফল দেখুন, বিশেষ করে ভোলার স্যাটেলাইট নমুনা।", "Open the sample cases, especially the Bhola satellite case."],
  ] }],
  [(p) => /^\/cases\/[^/]+$/.test(p), { title: "কেসের পাতা", en: "Case page", points: [
    ["উপরে যাচাইয়ের অবস্থা: কাগজ জমা থেকে রিপোর্ট পর্যন্ত ৫টি ধাপ।", "Tracker: five steps from papers to report."],
    ["“যা মেলেনি” অংশে প্রতিটি অমিলের উৎস-বোতাম নথির সেই ঘরটি খোলে।", "Each mismatch opens its source field in the document."],
    ["স্যাটেলাইট অংশে মানচিত্রে সীমানা এঁকে যাচাই চালানো যায়।", "Draw the plot on the map to run a satellite check."],
    ["“PDF রিপোর্ট” বোতামে পুরো ফল নামানো যায়।", "“PDF রিপোর্ট” downloads the report."],
  ] }],
  [(p) => p.includes("/timeline"), { title: "মালিকানার ইতিহাস", en: "Ownership history", points: [
    ["কেসের নথি থেকে কে কবে মালিক হলেন, তার সময়রেখা।", "Who owned the plot and when, built from the case documents."],
  ] }],
  [(p) => p.startsWith("/find") || p === "/cases" || p.startsWith("/upload"), { title: "কেস খোঁজা ও নতুন কেস", en: "Find or start a case", points: [
    ["বিভাগ, জেলা, মৌজা ও দাগ দিয়ে আগের কেস খুঁজুন।", "Search by division, district, mouza and dag."],
    ["না পেলে “নতুন কেস শুরু করুন”, তারপর নথি upload করুন।", "Not found? Start a new case and upload documents."],
  ] }],
  [(p) => p.startsWith("/escrow"), { title: "বায়না এসক্রো", en: "Earnest-money escrow", points: [
    ["টাকা থাকে অংশীদার ব্যাংকে; শর্ত মিললে ছাড়, না মিললে ফেরত।", "Money stays with a partner bank; released or refunded by conditions."],
    ["ডেমোতে ব্যাংক নমুনা; কোনো আসল টাকা নড়ে না।", "The demo bank is a mock; no real money moves."],
  ] }],
  [(p) => p.startsWith("/guardian"), { title: "প্রবাসী গার্ডিয়ান", en: "Migrant guardian", points: [
    ["খতিয়ানের কপি রাখুন; প্রতি মাসে নতুন কপির সঙ্গে মিলিয়ে বদল জানানো হয়।", "Keep a khatian copy; monthly comparison alerts on changes."],
  ] }],
  [(p) => p.startsWith("/demo"), { title: "নমুনা ডেটা", en: "Demo data", points: [
    ["প্রতিটি নমুনা প্যাক এক ক্লিকে আপনার নিজের নতুন কেস তৈরি করে; প্রস্তুত নমুনা কেস বদলায় না।", "One click makes your own new case; prepared samples never change."],
    ["সব নথি কৃত্রিম, “নমুনা / SAMPLE” ছাপ দেওয়া।", "All documents are synthetic and watermarked SAMPLE."],
  ] }],
  [(p) => p.startsWith("/how-it-works"), { title: "কীভাবে কাজ করে", en: "How it works", points: [
    ["কাগজ যাচাই আর মাটি যাচাই, দুটো ধাপ ধাপে বোঝানো।", "Paper check and ground check, step by step."],
  ] }],
  [(p) => p.startsWith("/docs"), { title: "ডকস", en: "Docs", points: [
    ["বাঁ পাশের সূচি থেকে যেকোনো অংশে যান।", "Use the table of contents to jump to a section."],
  ] }],
];
const FALLBACK: Guide = { title: "সাহায্য", en: "Help", points: [["পুরো গাইড চালিয়ে মূল অংশগুলো দেখে নিন।", "Run the full guide to see the main parts."]] };

export function HelpButton() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  if (pathname === "/login" || pathname === "/offline" || pathname.startsWith("/verify/")) return null;
  const guide = GUIDES.find(([m]) => m(pathname))?.[1] ?? FALLBACK;
  const casePath = /^\/cases\/[^/]+$/.test(pathname) ? pathname : undefined;
  return (
    <>
      <button type="button" aria-haspopup="dialog" aria-label="এই পাতার সাহায্য (Help for this page)" onClick={() => setOpen(true)}
        className="fixed bottom-24 right-4 z-40 inline-flex h-12 w-12 items-center justify-center rounded-full bg-accent text-xl font-bold text-white shadow-overlay transition-transform hover:-translate-y-0.5 md:bottom-6 md:right-6">
        <span aria-hidden="true">?</span>
      </button>
      <Modal open={open} onClose={() => setOpen(false)} title={<>{guide.title}<En className="text-muted">{guide.en}</En></>}
        footer={<>
          <Link href="/how-it-works" onClick={() => setOpen(false)} className="inline-flex min-h-11 flex-col justify-center rounded-[var(--radius-control)] border border-line bg-surface px-4 text-sm font-semibold text-ink hover:bg-bg">কীভাবে কাজ করে<En>How it works</En></Link>
          <button type="button" onClick={() => { setOpen(false); startTour(casePath ? 2 : 0, casePath); }} className="min-h-11 rounded-[var(--radius-control)] bg-accent px-4 text-sm font-semibold text-white shadow-rest">
            {casePath ? "এই কেসে গাইড চালান" : "পুরো গাইড শুরু করুন"}<En>{casePath ? "Guide on this case" : "Start the full guide"}</En>
          </button>
        </>}>
        <ul className="space-y-3">
          {guide.points.map(([bnText, en]) => (
            <li key={en} className="rounded-[var(--radius-control)] border border-edge bg-bg/60 p-3 text-sm leading-6">{bnText}<En className="mt-0.5 text-muted">{en}</En></li>
          ))}
        </ul>
      </Modal>
    </>
  );
}
