// Bangladesh's 8 divisions (বিভাগ) and 64 districts (জেলা), in Bangla.
// Upazila and mouza are free text with suggestions from existing cases (no full list in the app).

export const divisions: { name: string; districts: string[] }[] = [
  { name: "ঢাকা", districts: ["ঢাকা", "গাজীপুর", "নারায়ণগঞ্জ", "নরসিংদী", "মানিকগঞ্জ", "মুন্সিগঞ্জ", "টাঙ্গাইল", "কিশোরগঞ্জ", "ফরিদপুর", "গোপালগঞ্জ", "মাদারীপুর", "শরীয়তপুর", "রাজবাড়ী"] },
  { name: "চট্টগ্রাম", districts: ["চট্টগ্রাম", "কক্সবাজার", "রাঙ্গামাটি", "বান্দরবান", "খাগড়াছড়ি", "ফেনী", "নোয়াখালী", "লক্ষ্মীপুর", "কুমিল্লা", "চাঁদপুর", "ব্রাহ্মণবাড়িয়া"] },
  { name: "রাজশাহী", districts: ["রাজশাহী", "নাটোর", "নওগাঁ", "চাঁপাইনবাবগঞ্জ", "পাবনা", "সিরাজগঞ্জ", "বগুড়া", "জয়পুরহাট"] },
  { name: "খুলনা", districts: ["খুলনা", "বাগেরহাট", "সাতক্ষীরা", "যশোর", "ঝিনাইদহ", "মাগুরা", "নড়াইল", "কুষ্টিয়া", "চুয়াডাঙ্গা", "মেহেরপুর"] },
  { name: "বরিশাল", districts: ["বরিশাল", "ভোলা", "পটুয়াখালী", "পিরোজপুর", "ঝালকাঠি", "বরগুনা"] },
  { name: "সিলেট", districts: ["সিলেট", "মৌলভীবাজার", "হবিগঞ্জ", "সুনামগঞ্জ"] },
  { name: "রংপুর", districts: ["রংপুর", "দিনাজপুর", "ঠাকুরগাঁও", "পঞ্চগড়", "নীলফামারী", "লালমনিরহাট", "কুড়িগ্রাম", "গাইবান্ধা"] },
  { name: "ময়মনসিংহ", districts: ["ময়মনসিংহ", "জামালপুর", "শেরপুর", "নেত্রকোনা"] },
];

export const divisionOf = (district: string): string | undefined =>
  divisions.find((d) => d.districts.includes(district.trim()))?.name;

const BN_DIGITS = "০১২৩৪৫৬৭৮৯";

/** Compare identifiers and names typed in Bangla or ASCII digits, ignoring case and spaces. */
export const norm = (s: string | null | undefined): string =>
  (s ?? "").replace(/[০-৯]/g, (d) => String(BN_DIGITS.indexOf(d))).replace(/\s+/g, " ").trim().toLowerCase();

/** Old test cases with no district or a garbled ("??????") mouza are hidden from lists and suggestions (data is kept). */
export const isListedLand = (l: { district?: string | null; mouza?: string | null; upazila?: string | null }): boolean =>
  Boolean(l.district?.trim()) && !/\?{2,}/.test(`${l.mouza ?? ""}${l.upazila ?? ""}`);
