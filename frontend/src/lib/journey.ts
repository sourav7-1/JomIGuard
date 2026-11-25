// The buyer's journey for one plot. Step status comes from the backend
// (app/services/journey.py), so the case page, dashboard and PDF agree.

export type StepStatus = "done" | "action" | "waiting" | "locked" | "todo";
export type StepKey = "location" | "documents" | "paper" | "ground" | "report" | "seller" | "escrow" | "guardian";
export type Phase = "before" | "during" | "after";
export type JourneyStep = { n: number; key: string; phase: Phase; status: StepStatus; note_bn?: string };

export const STEP_LABELS: Record<StepKey, { bn: string; en: string }> = {
  location: { bn: "জমি চিহ্নিত", en: "Mark the plot" },
  documents: { bn: "কাগজ জমা", en: "Add papers" },
  paper: { bn: "কাগজ যাচাই", en: "Paper check" },
  ground: { bn: "মাটি যাচাই", en: "Ground check" },
  report: { bn: "রিপোর্ট ও সিদ্ধান্ত", en: "Report and decision" },
  seller: { bn: "বিক্রেতা যাচাই", en: "Seller check" },
  escrow: { bn: "বায়না এসক্রো", en: "Bayna escrow" },
  guardian: { bn: "প্রবাসী গার্ডিয়ান", en: "Probashi guardian" },
};

export const PHASE_LABELS: Record<Phase, { bn: string; en: string }> = {
  before: { bn: "কেনার আগে", en: "Before buying" },
  during: { bn: "কেনার সময়", en: "While buying" },
  after: { bn: "কেনার পরে", en: "After buying" },
};

export const STATUS_LABELS: Record<StepStatus, { bn: string; en: string }> = {
  done: { bn: "শেষ", en: "Done" },
  action: { bn: "আপনার কাজ", en: "Your move" },
  waiting: { bn: "চলছে", en: "In progress" },
  locked: { bn: "আগের ধাপ বাকি", en: "Needs an earlier step" },
  todo: { bn: "শুরু হয়নি", en: "Not started" },
};

// English for the backend's Bangla step notes (the API sends note_bn only).
const NOTE_EN: Partial<Record<StepKey, Partial<Record<StepStatus, string>>>> = {
  location: { action: "Draw the plot outline on the map" },
  documents: { action: "Upload the land papers, or retry the ones that could not be read", waiting: "Papers are being read" },
  paper: { locked: "Add papers in step 2 first", waiting: "Cross-check runs when every paper is read", action: "Cross-check the papers (again)" },
  ground: { locked: "Draw the plot outline in step 1 first", waiting: "Satellite check is running", action: "Run the satellite check" },
  report: { locked: "Finish the paper check in step 3 first", action: "PDF is ready; the ground check is still open" },
  seller: { todo: "Verify the seller's identity" },
  escrow: { todo: "Start a bayna escrow" },
  guardian: { todo: "After buying, put the khatian under watch" },
};

export function stepNote(step: JourneyStep, en: boolean): string {
  if (!en) return step.note_bn ?? "";
  return NOTE_EN[step.key as StepKey]?.[step.status] ?? "";
}

/** The first step that needs the user: action, then waiting, then locked/todo. Default open panel. */
export function currentStep(steps: JourneyStep[]): number {
  const pick = (s: StepStatus[]) => steps.find((x) => s.includes(x.status))?.n;
  return pick(["action"]) ?? pick(["waiting"]) ?? pick(["locked", "todo"]) ?? 1;
}

export type RiskBadgeLevel = "low" | "medium" | "high" | "unknown" | "incomplete";

/** Badge for a case: a low risk never shows as low while anything could not be checked. */
export function riskBadge(risk: string | null | undefined, complete: boolean): RiskBadgeLevel {
  if (risk === "high" || risk === "medium") return risk;
  if (risk === "low") return complete ? "low" : "incomplete";
  return "unknown";
}

type PlotCase = { district: string; mouza: string; dag_no: string; summary: { updated_at: string } };
const plotKey = (s: string) => s.replace(/[০-৯]/g, (d) => String("০১২৩৪৫৬৭৮৯".indexOf(d))).replace(/\s+/g, " ").trim().toLowerCase();

/** Cases on the same plot (district + mouza + dag), newest first in each group; nothing is dropped. */
export function groupByPlot<T extends PlotCase>(cases: T[]): T[][] {
  const groups = new Map<string, T[]>();
  for (const c of [...cases].sort((a, b) => b.summary.updated_at.localeCompare(a.summary.updated_at))) {
    const key = [c.district, c.mouza, c.dag_no].map(plotKey).join("|");
    groups.set(key, [...(groups.get(key) ?? []), c]);
  }
  return [...groups.values()];
}
