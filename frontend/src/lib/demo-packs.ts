// Judge demo content. Packs: backend/app/scripts/demo_data/packs (ml/synth/demo_packs.py).
// `expected` is the ACTUAL result recorded by uploading each pack through the app; null until
// it has been recorded (the page then says so instead of guessing).

export type Expected = { risk: string; findings: string[]; note?: string; recordedAt: string };
export type DemoPack = { id: string; title: string; en: string; shows: string; showsEn: string; expected: Expected | null };

export const demoPacks: DemoPack[] = [
  { id: "A", title: "সব মিলেছে", en: "All papers agree", expected: null,
    shows: "খতিয়ান, দলিল ও নামজারিতে মালিক, অংশ, দাগ ও মৌজা একই।", showsEn: "Owner, share, plot and mouza agree across khatian, deed and mutation." },
  { id: "B", title: "বিক্রেতা বেশি বিক্রি করছেন", en: "Seller sells more than their share", expected: null,
    shows: "দলিলে হস্তান্তরিত জমি খতিয়ানে বিক্রেতার অংশের চেয়ে বেশি।", showsEn: "The deed transfers more land than the seller's share on the khatian." },
  { id: "C", title: "দাগ নম্বর অমিল", en: "Plot (dag) number differs", expected: null,
    shows: "দলিলের তফসিলের দাগ নম্বর খতিয়ানের দাগের সঙ্গে মেলে না।", showsEn: "The deed's plot number does not match the khatian." },
  { id: "D", title: "ওয়ারিশ বাদ", en: "An heir is missing from the mutation", expected: null,
    shows: "ওয়ারিশ সনদের একজন জীবিত ওয়ারিশের নাম নামজারিতে নেই।", showsEn: "A living heir on the heir certificate is missing from the mutation." },
  { id: "E", title: "হাতে লেখার মতো দলিল", en: "Handwritten-style deed", expected: null,
    shows: "দলিলটি বাঁকা, কালির মতো লেখায়; পড়া কতটা ঠিক হয় তা দেখায়।", showsEn: "A slanted, ink-style deed: shows how well it is read." },
];

export type DemoPlot = { id: string; title: string; en: string; shows: string; showsEn: string; caseHref: string | null; expected: string | null; expectedEn: string | null };

export const demoPlots: DemoPlot[] = [
  { id: "bhola", title: "ভোলা · মেঘনার পাড়", en: "Bhola, Meghna bank (water rising)",
    shows: "ফেব্রুয়ারিতে আশেপাশে পানি ২০১৯-এ ২৮.১% থেকে ২০২৫-এ ৬৫.০%।",
    showsEn: "February water nearby went from 28.1% in 2019 to 65.0% in 2025.",
    caseHref: "/cases/3122299c-4917-5c21-827d-598119df27ef",
    expected: "(a) শুকনো মৌসুমেও পানি, (g) পানি বছর বছর বাড়ছে; নমুনা কেসে খতিয়ান 'নাল' থাকায় (d)-ও।",
    expectedEn: "(a) water even in the dry season, (g) water rising year by year; also (d) because the sample case's khatian says 'nal'." },
  { id: "gazipur", title: "গাজীপুর · ছোট বর্গ প্লট", en: "Gazipur square (stable)",
    shows: "যেখানে বছর বছর বড় কোনো বদল নেই, সেখানে ফল কেমন দেখায়।",
    showsEn: "What the result looks like where nothing big changes from year to year.",
    caseHref: "/cases/101d3448-72b2-4774-8940-920f358ba2e8",
    // live check recorded 2026-11-20 (sentinel + Earth Engine)
    expected: "কোনো স্যাটেলাইট ফলাফল নেই। আশেপাশে পানি প্রায় ০–০.৩%; গাছে ঢাকা জায়গার প্রবণতা প্রায় ৪০.৮% থেকে ৩৭.০%, স্থায়ী বদল নয়। ২০২২ ও ২০২৪ কম নির্ভরযোগ্য বছর হিসেবে বাদ।",
    expectedEn: "No satellite findings. Water nearby is about 0–0.3%; tree cover trends from about 40.8% to 37.0%, not a lasting change. 2022 and 2024 left out as low-confidence years." },
];

export const preparedCases: { href: string; title: string; en: string; line: string; lineEn: string }[] = [
  { href: "/cases/66c09208-d737-59f0-937e-de349f50899a", title: "কেস ০০০০১", en: "Case 00001", line: "উচ্চ ঝুঁকি: বিক্রেতা খতিয়ানের অংশের চেয়ে বেশি জমি বিক্রি করছেন; উৎসের ঘর দেখুন।", lineEn: "High risk: the seller is selling more land than their khatian share; see the source field." },
  { href: "/cases/6c530a00-cc5c-5c6b-a341-ae4491761d4e", title: "কেস ০০০২৬", en: "Case 00026", line: "সাধারণ বিক্রয়; আগের দলিলের প্রমাণ, আর বায়না এসক্রোর নমুনা।", lineEn: "Ordinary sale; earlier-deed evidence and a bayna escrow sample." },
  { href: "/cases/801bc1b6-b43c-5147-9b4f-b0baa3815cd0", title: "কেস ০০০২৯", en: "Case 00029", line: "পারিবারিক (ওয়ারিশ) কেস; মালিকানার ইতিহাসের সময়রেখা।", lineEn: "Family (inheritance) case; ownership history timeline." },
  { href: "/cases/3122299c-4917-5c21-827d-598119df27ef", title: "ভোলা · চর মেঘনা", en: "Bhola satellite case", line: "কাগজে চাষের জমি, স্যাটেলাইটে আশেপাশে পানি বাড়ছে।", lineEn: "Cropland on paper; satellite shows water rising nearby." },
];
