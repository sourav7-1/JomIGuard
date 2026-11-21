// Synthetic sample documents for the judge's own case (backend app/api/demo.py, /demo/lands/...).
// Each file is fetched as a File and then uploaded through the normal upload path.

export async function fetchSampleFile(url: string, name: string): Promise<File> {
  const res = await fetch(url, { credentials: "include" });
  if (!res.ok) {
    const detail = await res.json().then((b: { detail?: unknown }) => b.detail).catch(() => null);
    throw new Error(typeof detail === "string" ? detail : "নমুনা ফাইল আনা যায়নি। (Could not load the sample.)");
  }
  return new File([await res.blob()], name, { type: "image/png" });
}

export type SampleExpected = { risk_level: string; headline_bn: string; findings: { rule_id: string; title_bn: string }[] };
export type SampleSetInfo = { scenario: string; files: { name: string; doc_type: string }[]; expected: SampleExpected };

export const sampleScenarios = [
  { id: "A", title: "সব মিলেছে", en: "All papers agree", see: "কম ঝুঁকি; কোনো অমিল থাকার কথা নয়।", seeEn: "Low risk, no mismatch." },
  { id: "B", title: "বিক্রেতা বেশি বিক্রি করছেন", en: "Seller sells more than their share", see: "উচ্চ ঝুঁকি: দলিলের জমি বিক্রেতার অংশের চেয়ে বেশি।", seeEn: "High risk: the deed sells more than the seller's share." },
  { id: "C", title: "দাগ নম্বর অমিল", en: "Plot (dag) number differs", see: "উচ্চ ঝুঁকি: দলিলের দাগ খতিয়ানে নেই।", seeEn: "High risk: the deed's plot is not on the khatian." },
  { id: "D", title: "ওয়ারিশ বাদ", en: "Heir missing from the mutation", see: "মাঝারি ঝুঁকি: একজন ওয়ারিশের নাম নামজারিতে নেই।", seeEn: "Medium risk: an heir is missing from the mutation." },
  { id: "E", title: "হাতে লেখার মতো দলিল", en: "Handwritten-style deed", see: "ঠিকমতো পড়া গেলে কম ঝুঁকি; বাঁকা লেখা কতটা পড়া যায় তা দেখায়।", seeEn: "Low risk if read correctly; shows how slanted ink is read." },
] as const;

export const RISK_BN: Record<string, string> = { high: "উচ্চ ঝুঁকি", medium: "মাঝারি ঝুঁকি", low: "কম ঝুঁকি" };

// Which sample set was added to a case, so the result page can compare expected vs actual.
// Per-browser convenience only: missing storage just hides the comparison banner.
const key = (landId: string) => `jg-sample-${landId}`;
export type SampleRecord = { scenario: string; title: string; expected: SampleExpected };
export function rememberSample(landId: string, rec: SampleRecord) {
  try { localStorage.setItem(key(landId), JSON.stringify(rec)); } catch { /* storage blocked */ }
}
export function recalledSample(landId: string): SampleRecord | null {
  try { return JSON.parse(localStorage.getItem(key(landId)) ?? "null") as SampleRecord | null; } catch { return null; }
}
