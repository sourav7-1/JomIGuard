// Shared explainer content for /how-it-works and /docs. Every fact here comes from the repo:
// satellite rules from backend/app/services/satellite_findings.py, limits from README.md.

/** Satellite findings (paper vs ground), letters as used in the project. */
export const satelliteFindings: { letter: string; title: string; en: string; trigger: string; next: string }[] = [
  { letter: "a", title: "শুকনো মৌসুমেও আশেপাশে পানি", en: "Water around the plot in the dry season",
    trigger: "কোনো বছরের ফেব্রুয়ারিতে প্লটের আশেপাশের অনেকটা জায়গায় পানি।",
    next: "শুকনো ও বর্ষা দুই মৌসুমে নিজে বা আমিন দিয়ে জমিতে গিয়ে দেখুন, আশেপাশের লোকজনকে জিজ্ঞেস করুন।" },
  { letter: "b", title: "কোনো এক বছরে হঠাৎ বেশি পানি", en: "A sudden water spike in one year",
    trigger: "এক বছরের পানি প্রবণতা-রেখা ও পাশের বছরগুলোর চেয়ে অনেক বেশি।",
    next: "সেই বছর বন্যা, জলাবদ্ধতা বা পুকুর কাটা হয়েছিল কি না স্থানীয়দের কাছে জানুন।" },
  { letter: "c", title: "আশেপাশে গাছ কমেছে", en: "Tree cover dropped",
    trigger: "গাছে ঢাকা জায়গা স্থায়ীভাবে কমেছে (শেষের বছরগুলোতেও কম), অন্তত ৪টি পরিষ্কার বছরে।",
    next: "জমিতে গিয়ে দেখুন গাছ কাটা, নতুন ঘর, রাস্তা বা মাটি ভরাট হয়েছে কি না।" },
  { letter: "d", title: "কাগজে চাষের জমি, ছবিতে পানি", en: "Paper says cropland, image shows water",
    trigger: "খতিয়ানে শ্রেণী নাল/ধানী/কৃষি, আর (a) পাওয়া গেছে।",
    next: "মাঠে জমির আসল অবস্থা দেখুন, ভূমি অফিসে খতিয়ানের শ্রেণী যাচাই করুন।" },
  { letter: "e", title: "কাগজে বাগান, ছবিতে গাছ কমেছে", en: "Paper says orchard, trees dropped",
    trigger: "খতিয়ানে শ্রেণী বাগান, আর (c) পাওয়া গেছে।",
    next: "মাঠে বাগান এখনো আছে কি না দেখুন, ভূমি অফিসে শ্রেণী যাচাই করুন।" },
  { letter: "g", title: "আশেপাশে পানি বছর বছর বাড়ছে", en: "Water rising year after year",
    trigger: "পানির প্রবণতা স্থায়ীভাবে বাড়ছে (Theil-Sen ঢাল), অন্তত ৪টি পরিষ্কার বছরে।",
    next: "নদীভাঙন হচ্ছে কি না খোঁজ নিন, সর্বশেষ মৌজা ম্যাপ দেখুন, আমিন দিয়ে জমি মাপুন।" },
  { letter: "f", title: "স্যাটেলাইট প্রমাণ যথেষ্ট নয়", en: "Not enough satellite evidence",
    trigger: "৪টির কম বছরের পরিষ্কার ছবি। এটি কোনো পাস নয়।",
    next: "পরে আবার যাচাই চালান; ততক্ষণ নিজে জমিতে গিয়ে দেখুন।" },
];

/** What the app does not tell you. */
export const limits: [string, string][] = [
  ["এটি মালিকানার নিশ্চয়তা নয়; অ্যাপ শুধু বলে কী মিলেছে, কী মেলেনি আর এরপর কী করবেন। এটি আইনি পরামর্শও নয়।", "Not a title guarantee and not legal advice: it shows what matched, what did not, and what to do next."],
  ["মামলা, দখল বা বন্ধক অ্যাপ দেখতে পায় না; এগুলো কাগজে না থাকলে ধরা পড়ে না।", "It cannot see court cases, possession or mortgages."],
  ["স্যাটেলাইট পিক্সেল ১০ মিটার, তাই ফল প্লটের চারপাশের প্রায় ২০০ মিটার এলাকার, প্লটের ভেতরের নয়।", "10 m pixels: results describe ~200 m around the plot, not inside it."],
  ["ছবি প্রতি বছরের ফেব্রুয়ারির (শুকনো মৌসুম); বর্ষার বন্যা এতে ধরা পড়ে না।", "Images are from February (dry season); monsoon floods are not covered."],
  ["OCR ও তথ্য পড়ায় ভুল হতে পারে; উৎসের ঘর ও মূল পাতা মিলিয়ে দেখুন।", "OCR and extraction can misread; check the source field and page."],
  ["ডেমোর ব্যাংক (এসক্রো) ও পরিচয় যাচাই নমুনা; কোনো আসল টাকা বা e-KYC নেই।", "The demo bank (escrow) and identity check are mocks."],
];
