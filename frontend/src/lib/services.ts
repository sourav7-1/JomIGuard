// The six JomiGuard Sentinel services: one source for the home grid, the location picker and /help.

export type ServiceId = "documents" | "history" | "satellite" | "escrow" | "guardian" | "seller";

export type Service = {
  id: ServiceId;
  title: string;
  titleEn: string;
  line: string;
  lineEn: string;
  start: { label: string; labelEn: string; href: string };
  icon: string; // 24x24 stroke path
  howTo: string[];
  howToEn: string[];
  satellite?: boolean;
};

export const BHOLA_CASE = "/cases/3122299c-4917-5c21-827d-598119df27ef";

export const services: Service[] = [
  {
    id: "documents",
    title: "কাগজ যাচাই",
    titleEn: "Document check",
    line: "খতিয়ান, দলিল ও নামজারির তথ্য মিলিয়ে কোথায় অমিল, তা উৎসসহ দেখায়।",
    lineEn: "Cross-checks khatian, deed and mutation data and shows each mismatch with its source.",
    start: { label: "শুরু করুন", labelEn: "Start", href: "/find?service=documents" },
    icon: "M6 3.75h8l4 4v12.5H6z M14 3.75v4h4 M9 12h6 M9 15.5h6",
    howTo: [
      "বিভাগ, জেলা, উপজেলা ও মৌজা বেছে জমির কেস খুঁজুন বা নতুন কেস শুরু করুন।",
      "খতিয়ান, দলিল, নামজারি বা ওয়ারিশ সনদের ছবি বা PDF যোগ করুন।",
      "পড়া তথ্য মিলিয়ে দেখুন; প্রতিটি অমিলের পাশে কোন নথির কোন ঘর থেকে এসেছে তা দেখা যায়।",
      "“এখন কী করবেন” তালিকা ধরে কাজ করুন এবং PDF রিপোর্ট নিন।",
    ],
    howToEn: [
      "Pick division, district, upazila and mouza to find a land case or start a new one.",
      "Add a photo or PDF of the khatian, deed, mutation or heir certificate.",
      "Review the extracted data; each mismatch shows which document and field it came from.",
      "Work through the “What to do next” list and download the PDF report.",
    ],
  },
  {
    id: "history",
    title: "মালিকানার ইতিহাস",
    titleEn: "Ownership history",
    line: "কেসের নথি থেকে কে কবে মালিক হলেন, তার সময়রেখা দেখায়।",
    lineEn: "Shows a timeline of who owned the plot and when, from the case documents.",
    start: { label: "নমুনা দেখুন", labelEn: "See sample", href: "/cases/801bc1b6-b43c-5147-9b4f-b0baa3815cd0/timeline" },
    icon: "M4 6h12 M12 2l4 4-4 4 M20 18H8 M12 14l-4 4 4 4",
    howTo: [
      "একটি কেসে খতিয়ান, দলিল ও নামজারির কাগজ যোগ করুন।",
      "কেসের পাতায় “এই কেসের টাইমলাইন দেখুন” চাপুন।",
      "বিক্রি, নামজারি ও উত্তরাধিকারের ঘটনা তারিখ অনুযায়ী দেখুন; অংশ নথিতে যা লেখা তাই দেখানো হয়, হিসাব করা হয় না।",
    ],
    howToEn: [
      "Add khatian, deed and mutation papers to a case.",
      "On the case page, press “See this case’s timeline”.",
      "See sales, mutations and inheritance by date; shares are shown as printed, never calculated.",
    ],
  },
  {
    id: "satellite",
    title: "স্যাটেলাইট যাচাই",
    titleEn: "Satellite check",
    line: "শুকনো মৌসুমের ছবিতে প্লটের আশেপাশে পানি ও গাছের বদল, খতিয়ানের সঙ্গে মিলিয়ে।",
    lineEn: "Dry-season imagery of water and tree changes around the plot, compared with the khatian.",
    start: { label: "শুরু করুন", labelEn: "Start", href: "/find?service=satellite" },
    icon: "M4 12a8 8 0 0 1 8-8 M7 12a5 5 0 0 1 5-5 M11 15l7-7 M14 8h4v4 M10 18l-2 2 M14 14l6 6-2 2-6-6",
    satellite: true,
    howTo: [
      "জমির কেস খুলুন এবং “স্যাটেলাইট যাচাই” অংশে মানচিত্রে প্লটের কোণগুলোতে ক্লিক করে সীমানা আঁকুন।",
      "“সীমানা রাখুন”, তারপর “স্যাটেলাইট যাচাই করুন” চাপুন; ফল আসতে সাধারণত এক থেকে কয়েক মিনিট লাগে।",
      "ফল প্লটের চারপাশের প্রায় ২০০ মিটার এলাকার; মাঠে গিয়ে নিজে মিলিয়ে দেখুন।",
    ],
    howToEn: [
      "Open the land case and draw the plot boundary on the map in the “Satellite check” section.",
      "Press “Save boundary”, then “Run satellite check”; results usually take one to a few minutes.",
      "Results cover about 200 m around the plot; check on the ground yourself.",
    ],
  },
  {
    id: "escrow",
    title: "বায়না এসক্রো",
    titleEn: "Bayna escrow",
    line: "শর্ত মিললে বায়নার টাকা ছাড়, না মিললে ফেরত; টাকা থাকে ব্যাংক অংশীদারের কাছে (ডেমোতে নমুনা ব্যাংক)।",
    lineEn: "Earnest money is released when conditions match and refunded when they do not; a partner bank holds it (a sample bank in the demo).",
    start: { label: "নমুনা দেখুন", labelEn: "See sample", href: "/escrow/demo-00026" },
    icon: "M3 8h18v11H3z M3 11h18 M7 15h4 M7 4h10",
    howTo: [
      "কেসের পাতা থেকে “বায়না escrow শুরু করুন” চাপুন।",
      "চুক্তির শর্ত দেখুন এবং ধাপগুলো (চুক্তি, টাকা জমা, শর্ত যাচাই, রেজিস্ট্রি, ছাড় বা ফেরত) অনুসরণ করুন।",
      "ডেমোতে ব্যাংক নমুনা; কোনো আসল টাকা জমা বা স্থানান্তর হয় না।",
    ],
    howToEn: [
      "Press “Start bayna escrow” on the case page.",
      "Read the contract conditions and follow the steps (agree, deposit, condition check, registration, release or refund).",
      "The bank is a sample in the demo; no real money is deposited or moved.",
    ],
  },
  {
    id: "guardian",
    title: "প্রবাসী গার্ডিয়ান",
    titleEn: "Probashi guardian",
    line: "কেনার পরে খতিয়ানের নতুন কপি আগেরটির সঙ্গে মিলিয়ে বদল ধরায়।",
    lineEn: "After purchase, compares a newer khatian copy with the previous one and flags changes.",
    start: { label: "শুরু করুন", labelEn: "Start", href: "/guardian" },
    icon: "M12 3 20 6v5c0 5-3.4 8.2-8 10-4.6-1.8-8-5-8-10V6z M9 11.5l2 2 4-4",
    howTo: [
      "“জমি যোগ করুন” দিয়ে নজরদারির জন্য খতিয়ান রাখুন।",
      "নতুন খতিয়ানের কপি হাতে upload করুন এবং “মাসিক যাচাই চালান” চাপুন।",
      "মালিক বদল লাল, ছোট বদল হলুদ, অপরিবর্তিত সবুজ দেখাবে।",
    ],
    howToEn: [
      "Use “Add land” to keep a khatian under watch.",
      "Upload the new khatian copy and press “Run monthly check”.",
      "Owner changes show red, small changes yellow, unchanged green.",
    ],
  },
  {
    id: "seller",
    title: "বিক্রেতা যাচাই",
    titleEn: "Seller identity check",
    line: "বিক্রেতাকে পরিচয় যাচাইয়ের link পাঠান; শুধু যাচাইয়ের ফল রাখা হয়।",
    lineEn: "Send the seller an identity-check link; only the result is kept.",
    start: { label: "শুরু করুন", labelEn: "Start", href: "/find?service=seller" },
    icon: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z M4 21a8 8 0 0 1 16 0 M16 15l2 2 3-3",
    howTo: [
      "জমির কেস খুলুন; দলিলের খসড়ায় থাকা বিক্রেতার নাম “বিক্রেতার পরিচয়” অংশে দেখাবে।",
      "“link তৈরি করুন” চেপে link বিক্রেতাকে পাঠান।",
      "বিক্রেতা সম্মতি দিয়ে যাচাই শেষ করলে ফল কেসে দেখাবে; NID নম্বর, ছবি বা সেলফি রাখা হয় না।",
    ],
    howToEn: [
      "Open the land case; the seller name from the draft deed shows in “Seller identity”.",
      "Press “Create link” and send it to the seller.",
      "When the seller consents and finishes, the result shows in the case; NID numbers, photos and selfies are not kept.",
    ],
  },
];

// Official government services we only refer to (each verified in a browser on 2026-11-20).
export const officialLinks = [
  { label: "সার্টিফাইড খতিয়ান ও মৌজা ম্যাপ", labelEn: "Certified khatian and mouza map", href: "https://dlrms.land.gov.bd/" },
  { label: "নামজারি (মিউটেশন) আবেদন", labelEn: "Mutation (namjari) application", href: "https://mutation.land.gov.bd/" },
  { label: "ভূমি উন্নয়ন কর", labelEn: "Land development tax", href: "https://ldtax.gov.bd/" },
];
