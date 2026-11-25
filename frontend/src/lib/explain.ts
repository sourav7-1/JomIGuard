// Shared explainer content for /how-it-works and /docs. Every fact here comes from the repo:
// satellite rules from backend/app/services/satellite_findings.py, limits from README.md.

/** Satellite findings (paper vs ground), letters as used in the project. */
export const satelliteFindings: { letter: string; title: string; en: string; trigger: string; triggerEn: string; next: string; nextEn: string }[] = [
  { letter: "a", title: "শুকনো মৌসুমেও আশেপাশে পানি", en: "Water around the plot in the dry season",
    trigger: "কোনো বছরের ফেব্রুয়ারিতে প্লটের আশেপাশের অনেকটা জায়গায় পানি।", triggerEn: "In some February, a large area around the plot is under water.",
    next: "শুকনো ও বর্ষা দুই মৌসুমে নিজে বা আমিন দিয়ে জমিতে গিয়ে দেখুন, আশেপাশের লোকজনকে জিজ্ঞেস করুন।", nextEn: "Visit the land yourself or with an amin in both dry and wet seasons, and ask the neighbours." },
  { letter: "b", title: "কোনো এক বছরে হঠাৎ বেশি পানি", en: "A sudden water spike in one year",
    trigger: "এক বছরের পানি প্রবণতা-রেখা ও পাশের বছরগুলোর চেয়ে অনেক বেশি।", triggerEn: "One year's water is far above the trend line and the years around it.",
    next: "সেই বছর বন্যা, জলাবদ্ধতা বা পুকুর কাটা হয়েছিল কি না স্থানীয়দের কাছে জানুন।", nextEn: "Ask local people whether there was a flood, waterlogging or a pond dug that year." },
  { letter: "c", title: "আশেপাশে গাছ কমেছে", en: "Tree cover dropped",
    trigger: "গাছে ঢাকা জায়গা স্থায়ীভাবে কমেছে (শেষের বছরগুলোতেও কম), অন্তত ৪টি পরিষ্কার বছরে।", triggerEn: "Tree cover dropped for good (still low in the latest years), over at least 4 clear years.",
    next: "জমিতে গিয়ে দেখুন গাছ কাটা, নতুন ঘর, রাস্তা বা মাটি ভরাট হয়েছে কি না।", nextEn: "Visit the land and see whether trees were cut or a house, road or earth fill appeared." },
  { letter: "d", title: "কাগজে চাষের জমি, ছবিতে পানি", en: "Paper says cropland, image shows water",
    trigger: "খতিয়ানে শ্রেণী নাল/ধানী/কৃষি, আর (a) পাওয়া গেছে।", triggerEn: "The khatian class is nal/dhani/cropland, and (a) was found.",
    next: "মাঠে জমির আসল অবস্থা দেখুন, ভূমি অফিসে খতিয়ানের শ্রেণী যাচাই করুন।", nextEn: "See the real state of the land on the ground and check the khatian class at the land office." },
  { letter: "e", title: "কাগজে বাগান, ছবিতে গাছ কমেছে", en: "Paper says orchard, trees dropped",
    trigger: "খতিয়ানে শ্রেণী বাগান, আর (c) পাওয়া গেছে।", triggerEn: "The khatian class is orchard, and (c) was found.",
    next: "মাঠে বাগান এখনো আছে কি না দেখুন, ভূমি অফিসে শ্রেণী যাচাই করুন।", nextEn: "See whether the orchard is still there and check the class at the land office." },
  { letter: "g", title: "আশেপাশে পানি বছর বছর বাড়ছে", en: "Water rising year after year",
    trigger: "পানির প্রবণতা স্থায়ীভাবে বাড়ছে (Theil-Sen ঢাল), অন্তত ৪টি পরিষ্কার বছরে।", triggerEn: "The water trend rises steadily (Theil-Sen slope) over at least 4 clear years.",
    next: "নদীভাঙন হচ্ছে কি না খোঁজ নিন, সর্বশেষ মৌজা ম্যাপ দেখুন, আমিন দিয়ে জমি মাপুন।", nextEn: "Find out whether there is river erosion, see the latest mouza map, and have an amin measure the land." },
  { letter: "f", title: "স্যাটেলাইট প্রমাণ যথেষ্ট নয়", en: "Not enough satellite evidence",
    trigger: "৪টির কম বছরের পরিষ্কার ছবি। এটি কোনো পাস নয়।", triggerEn: "Clear images for fewer than 4 years. This is not a pass.",
    next: "পরে আবার যাচাই চালান; ততক্ষণ নিজে জমিতে গিয়ে দেখুন।", nextEn: "Run the check again later; meanwhile, visit the land yourself." },
];

/** What the app does not tell you. */
export const limits: [string, string][] = [
  ["এটি মালিকানার নিশ্চয়তা নয়; অ্যাপ শুধু বলে কী মিলেছে, কী মেলেনি আর এরপর কী করবেন। এটি আইনি পরামর্শও নয়।", "It does not confirm ownership and is not legal advice: it shows what matched, what did not, and what to do next."],
  ["মামলা, দখল বা বন্ধক অ্যাপ দেখতে পায় না; এগুলো কাগজে না থাকলে ধরা পড়ে না।", "It cannot see court cases, possession or mortgages."],
  ["স্যাটেলাইট পিক্সেল ১০ মিটার, তাই ফল প্লটের চারপাশের প্রায় ২০০ মিটার এলাকার, প্লটের ভেতরের নয়।", "10 m pixels: results describe ~200 m around the plot, not inside it."],
  ["ছবি প্রতি বছরের ফেব্রুয়ারির (শুকনো মৌসুম); বর্ষার বন্যা এতে ধরা পড়ে না।", "Images are from February (dry season); monsoon floods are not covered."],
  ["OCR ও তথ্য পড়ায় ভুল হতে পারে; উৎসের ঘর ও মূল পাতা মিলিয়ে দেখুন।", "OCR and extraction can misread; check the source field and page."],
  ["ডেমোর ব্যাংক (এসক্রো) ও পরিচয় যাচাই নমুনা; কোনো আসল টাকা বা e-KYC নেই।", "The demo bank (escrow) and identity check are mocks."],
];
