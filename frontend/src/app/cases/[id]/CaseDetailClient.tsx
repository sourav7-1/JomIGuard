"use client";

import React, { useState, useEffect, useCallback, useSyncExternalStore } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  api,
  AssessmentDiff,
  CaseViewDocOut,
  DeedArchiveItemOut,
  FieldsMetaResponse,
  LandCaseViewOut,
  PlotGeometry,
  SatelliteCheckOut,
} from "@/lib/api";
import { SatellitePanel } from "@/components/case/SatellitePanel";
import PlotMap from "@/components/case/PlotMap";
import { SampleCompare } from "@/components/case/SampleCompare";
import { JourneyStepper } from "@/components/case/JourneyStepper";
import { NextActions } from "@/components/case/NextActions";
import { OwnershipTimeline } from "@/components/case/OwnershipTimeline";
import { DeedArchive } from "@/components/case/DeedArchive";
import { EscrowExplainer } from "@/components/case/EscrowExplainer";
import { useLang, useStrings, useEscrowFlow } from "@/lib/lang";
import { CaseSkeleton } from "@/components/ui/Skeleton";
import { Modal, useConfirm } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";
import { EmptyState } from "@/components/ui/EmptyState";
import { VerdictBox } from "@/components/ui/VerdictBox";
import { CheckItem } from "@/components/ui/CheckItem";
import { FindingCard, findingTone } from "@/components/ui/FindingCard";
import { CaseHeader, CaseSummaryTable, DocumentFieldsPanel } from "@/components/case";
import { SellerIdentityPanel } from "@/components/case/SellerIdentityPanel";
import { bnDigits } from "@/lib/digits";
import { STEP_LABELS, currentStep, riskBadge, stepNote, type JourneyStep, type StepKey } from "@/lib/journey";

interface CaseDetailClientProps {
  landId: string;
  source?: string;
  field?: string;
}

const RISK_BN: Record<string, string> = { low: "কম ঝুঁকি", medium: "মাঝারি ঝুঁকি", high: "উচ্চ ঝুঁকি" };
const RISK_EN: Record<string, string> = { low: "Low risk", medium: "Medium risk", high: "High risk" };
const LOAD_ERROR = "__load__";
// A rule's source field_path names a derived field; the document panel shows the printed one.
const printedField = (path: string) => path.replace(/name_normalized$/, "name").replace(/_(?:shatangsho|fraction)$/, "_text");

const PURPOSE: Record<StepKey, [string, string]> = {
  location: ["জমির ঠিকানা আর মানচিত্রে প্লটের সীমানা; স্যাটেলাইট যাচাই এই সীমানা ধরে হয়।", "The plot's address and its outline on the map; the satellite check uses this outline."],
  documents: ["খতিয়ান, দলিল, নামজারি ও ওয়ারিশ সনদ জমা দিন; প্রতিটি কাগজ পড়া হলে এখানে দেখাবে।", "Add the khatian, deed, mutation and heir certificate; each paper shows here once it is read."],
  paper: ["কাগজগুলো একে অন্যের সঙ্গে মেলানো: যা মেলেনি, যা মিলেছে, আর যা মেলানো যায়নি।", "The papers checked against each other: what did not match, what matched, and what could not be checked."],
  ground: ["স্যাটেলাইট ছবিতে প্লটের আশেপাশে পানি ও গাছের বদল।", "Changes in water and trees around the plot in satellite images."],
  report: ["ঝুঁকির সারাংশ, এই অ্যাপের সীমা, আর PDF রিপোর্ট।", "The risk summary, the limits of this app, and the PDF report."],
  seller: ["বায়নার আগে বিক্রেতার পরিচয় যাচাই; শুধু যাচাইয়ের ফল রাখা হয়।", "Check the seller's identity before the bayna; only the result is kept."],
  escrow: ["বায়নার টাকা অংশীদার ব্যাংকে থাকে; শর্ত মিললে ছাড়, না মিললে ফেরত।", "The bayna money stays with a partner bank; released if the conditions are met, refunded if not."],
  guardian: ["কেনার পরে খতিয়ানের কপি রেখে প্রতি মাসে নতুন কপির সঙ্গে মিলিয়ে বদল দেখা।", "After buying, keep a khatian copy and compare it with a new copy every month."],
};
const GATE_TARGET: Record<number, number> = { 3: 2, 4: 1, 5: 3 };

// URL hash "#step-N" is the open panel, so a step can be linked and Back works.
const subscribeHash = (cb: () => void) => { window.addEventListener("hashchange", cb); return () => window.removeEventListener("hashchange", cb); };
const hashStep = () => Number(/^#step-([1-8])/.exec(window.location.hash)?.[1] ?? 0);

export function CaseDetailClient({ landId, source, field }: CaseDetailClientProps) {
  const router = useRouter();
  const en = useLang() === "en";
  const strings = useStrings();
  const escrowFlow = useEscrowFlow();
  const t = (b: string, e: string) => (en ? e : b);
  const num = (v: number | string) => (en ? String(v) : bnDigits(v));
  const riskName = (level: string) => (en ? RISK_EN : RISK_BN)[level] ?? level;
  const [caseView, setCaseView] = useState<LandCaseViewOut | null>(null);
  const [check, setCheck] = useState<SatelliteCheckOut | null>(null);
  const [deedArchive, setDeedArchive] = useState<DeedArchiveItemOut[]>([]);
  const [fieldsMeta, setFieldsMeta] = useState<FieldsMetaResponse | null>(null);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [assessmentDiff, setAssessmentDiff] = useState<AssessmentDiff | null>(null);
  const [assessing, setAssessing] = useState(false);
  const [expandedPassed, setExpandedPassed] = useState(false);
  const [highlightField, setHighlightField] = useState<string | null>(null);
  const [actionBusy, setActionBusy] = useState<string | null>(null);
  const [escrowBusy, setEscrowBusy] = useState(false);
  const [paperTab, setPaperTab] = useState<"results" | "timeline" | "deeds">("results");
  // finding / timeline source viewer: the document page opens in a modal instead of scrolling away
  const [sourceView, setSourceView] = useState<{ docId: string; field: string | null } | null>(null);
  const hashed = useSyncExternalStore(subscribeHash, hashStep, () => 0);
  const toast = useToast();
  const { ask, dialog: confirmDialog } = useConfirm();

  const fetchData = useCallback(async () => {
    try {
      const [cv, meta, deeds, sat] = await Promise.all([
        api.getLandCaseView(landId),
        api.getFieldsMeta(),
        api.getLandDeeds(landId),
        api.getLatestSatelliteCheck(landId).catch(() => null), // 404 = no check yet
      ]);
      setCaseView(cv);
      setCheck(sat);
      setDeedArchive(deeds.items);
      setFieldsMeta(meta);
      setAssessmentDiff(cv.latest_assessment ? await api.getAssessmentDiff(landId, cv.latest_assessment.id).catch(() => null) : null);
      if (cv.documents.length > 0) {
        setSelectedDocId((prev) => (prev && cv.documents.some((d) => d.id === prev) ? prev : cv.documents[0].id));
      }
    } catch {
      setError(LOAD_ERROR);
    } finally {
      setLoading(false);
    }
  }, [landId]);

  const runAssessment = async () => {
    setAssessing(true);
    setError(null);
    try {
      await api.assessLand(landId);
      await fetchData();
      toast("ok", t("নতুন করে মিলিয়ে দেখা হয়েছে।", "Checked again."));
    } catch (e) {
      const msg = e instanceof Error ? e.message : strings.casePage.assessmentError;
      setError(msg);
      toast("bad", msg);
    } finally {
      setAssessing(false);
    }
  };

  const openSource = (docId: string, target: string | null) => {
    setHighlightField(target ? `${docId}:${target}` : null);
    setSourceView({ docId, field: target });
    if (target) window.setTimeout(() => document.querySelector(`dialog[open] [id="field-${docId}-${target}"]`)?.scrollIntoView({ behavior: "smooth", block: "center" }), 350);
  };
  const focusSource = (sourceId: string, fieldPath: string) => openSource(sourceId, printedField(fieldPath));

  const updateAction = async (actionId: string, done: boolean) => {
    setActionBusy(actionId);
    try {
      await api.updateAction(landId, actionId, done);
      await fetchData();
      toast("ok", done ? t("কাজটি শেষ হিসেবে রাখা হয়েছে।", "Task marked done.") : t("কাজটি আবার খোলা হয়েছে।", "Task reopened."));
    } catch (e) {
      toast("bad", e instanceof Error ? e.message : strings.casePage.assessmentError);
    } finally {
      setActionBusy(null);
    }
  };

  const startEscrow = async () => {
    const ok = await ask({
      title: t("বায়না escrow শুরু করবেন?", "Start bayna escrow?"),
      message: t("এই কেসের জন্য একটি নমুনা বায়না escrow চুক্তির খসড়া তৈরি হবে। ডেমোতে ব্যাংক নমুনা; কোনো আসল টাকা জমা বা স্থানান্তর হয় না।", "A sample bayna escrow draft will be created for this case. The bank is a sample in the demo; no real money is deposited or moved."),
      confirmLabel: t("escrow শুরু করুন", "Start escrow"),
    });
    if (!ok) return;
    setEscrowBusy(true);
    try {
      const deal = await api.createEscrow(landId, {
        price: "6000000", bayna: "500000",
        deadline: new Date(Date.now() + 60 * 86400000).toISOString().slice(0, 10),
      });
      toast("ok", t("escrow খসড়া তৈরি হয়েছে।", "Escrow draft created."));
      router.push(`/escrow/${deal.id}`);
    } catch (e) { toast("bad", e instanceof Error ? e.message : strings.casePage.assessmentError); }
    finally { setEscrowBusy(false); }
  };

  useEffect(() => {
    // Starts the async load; state updates occur when its request settles.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (!loading && source && field && caseView?.documents.some((doc) => doc.id === source)) {
      const target = printedField(field);
      window.setTimeout(() => {
        setSelectedDocId(source);
        setHighlightField(`${source}:${target}`);
        setSourceView({ docId: source, field: target });
        window.setTimeout(() => document.querySelector(`dialog[open] [id="field-${source}-${target}"]`)?.scrollIntoView({ behavior: "smooth", block: "center" }), 350);
      }, 0);
    }
  }, [loading, source, field, caseView]);

  if (loading) return <CaseSkeleton />;

  if (error === LOAD_ERROR || !caseView) {
    return (
      <div className="mx-auto max-w-2xl py-12">
        <EmptyState
          title={strings.casePage.caseNotFound}
          description={t("কেসের তথ্য লোড করতে সমস্যা হয়েছে।", "Could not load the case data.")}
          actionLabel={t("আমার কেসে ফিরুন", "Back to my cases")}
          actionHref="/dashboard"
        />
      </div>
    );
  }

  const steps = caseView.journey.steps as JourneyStep[];
  const active = hashed || currentStep(steps);
  const step = steps[active - 1];
  const goTo = (n: number) => {
    window.history.pushState(null, "", `#step-${n}`);
    window.dispatchEvent(new HashChangeEvent("hashchange"));
    window.setTimeout(() => document.getElementById("step-panel")?.scrollIntoView({ behavior: "smooth", block: "start" }), 0);
  };
  const assessment = caseView.latest_assessment;
  const reasons = caseView.journey.incomplete_reasons_bn ?? [];
  const geometry = (caseView.land as { geometry?: PlotGeometry | null }).geometry ?? null;
  const selectedDoc = caseView.documents.find((d) => d.id === selectedDocId) || caseView.documents[0];
  const metaFor = (docType: string | null | undefined) => (fieldsMeta ? (fieldsMeta as Record<string, typeof fieldsMeta.khatian>)[docType || "khatian"] || [] : []);
  const proposedDeed = caseView.documents.find((doc) => doc.role === "proposed_deed");
  const sellerRows = (proposedDeed?.latest_extraction?.data as { sellers?: { name: string }[] } | null)?.sellers || [];
  const sourceDoc = sourceView ? caseView.documents.find((d) => d.id === sourceView.docId) : undefined;
  const btn = "inline-flex min-h-11 items-center rounded-[var(--radius-control)] px-4 text-sm font-semibold";
  const primary = `${btn} bg-accent text-white shadow-rest hover:shadow-raised disabled:opacity-60`;
  const ghost = `${btn} border border-line bg-surface text-ink hover:bg-bg`;

  /** A step that needs an earlier one: say why and offer that step. */
  const gate = (s: JourneyStep) => {
    const target = GATE_TARGET[s.n];
    return (
      <div role="status" className="rounded-[var(--radius-card)] border border-dashed border-line bg-bg/60 p-4 text-sm leading-6">
        <p className="font-semibold text-ink">{stepNote(s, en)}</p>
        {target && <button type="button" onClick={() => goTo(target)} className={`${primary} mt-3`}>{en ? `Open step ${target}` : `ধাপ ${bnDigits(target)} খুলুন`}</button>}
      </div>
    );
  };
  /** Not blocking, but the user should know (e.g. unread papers above a partial result). */
  const notice = (s: JourneyStep, target?: number, action?: React.ReactNode) => (
    <div role="status" className="flex flex-col gap-2 rounded-[var(--radius-control)] border border-warn/40 bg-warn-bg p-3 text-sm sm:flex-row sm:items-center sm:justify-between">
      <span className="font-semibold text-ink">{stepNote(s, en)}</span>
      {action ?? (target ? <button type="button" onClick={() => goTo(target)} className={ghost}>{en ? `Open step ${target}` : `ধাপ ${bnDigits(target)} খুলুন`}</button> : null)}
    </div>
  );

  const docsPanel = (
    <div className="space-y-4">
      {!caseView.documents.length ? (
        <EmptyState title={strings.casePage.emptyDocList} description={strings.casePage.emptyDocDescription} actionLabel={t("কাগজ upload করুন", "Upload papers")} actionHref={`/upload/${landId}`} />
      ) : <>
        {step.status === "action" && notice(step, undefined, <Link href={`/upload/${landId}`} className={ghost}>{t("আবার চেষ্টা করুন", "Retry")}</Link>)}
        <CaseSummaryTable documents={caseView.documents} selectedDocId={selectedDoc.id} onSelectDoc={setSelectedDocId} />
        <div className="flex flex-wrap items-center gap-2">
          <Link href={`/upload/${landId}`} className={primary}>{t("+ আরো কাগজ যোগ করুন", "+ Add more papers")}</Link>
          <span className="text-xs text-muted">{t("upload পাতায় নমুনা কাগজের সেটও আছে।", "The upload page also has sample paper sets.")}</span>
        </div>
        <details id="source-document-panel" className="group rounded-[var(--radius-card)] border border-edge bg-surface">
          <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-semibold text-ink [&::-webkit-details-marker]:hidden">
            {t("নথির ছবি ও পড়া তথ্য দেখুন বা ঠিক করুন", "See or correct the document image and the data read from it")}
            <span aria-hidden="true" className="text-muted transition-transform group-open:rotate-180">▾</span>
          </summary>
          <div className="space-y-3 border-t border-line p-3">
            <div className="flex items-center gap-2 overflow-x-auto pb-1">
              {caseView.documents.map((d: CaseViewDocOut) => (
                <button key={d.id} type="button" onClick={() => setSelectedDocId(d.id)}
                  className={`flex min-h-11 items-center whitespace-nowrap rounded-xl border px-3.5 py-2 text-xs font-semibold ${d.id === selectedDoc.id ? "border-accent bg-accent text-surface" : "border-line bg-surface text-ink hover:bg-bg"}`}>{d.label_bn}</button>
              ))}
            </div>
            <DocumentFieldsPanel key={selectedDoc.id} document={selectedDoc} fieldMetaList={metaFor(selectedDoc.doc_type)} onExtractionUpdated={fetchData} highlightField={highlightField} />
          </div>
        </details>
      </>}
    </div>
  );

  // OCR-read numbers (assessment.to_verify) get their own block below, not the plain list
  const toVerify = assessment?.to_verify ?? [];
  const toVerifyText = new Set(toVerify.map((r) => r.message_bn));
  const skippedReasons = [...new Set((assessment?.coverage.checks_skipped ?? []).map((c) => c.reason_bn))].filter((r) => !toVerifyText.has(r));
  const sourceButtons = (sources: NonNullable<typeof toVerify[number]["sources"]> | undefined) => (
    <div className="flex flex-wrap gap-2">{(sources ?? []).map((src, j) => <button key={`${src.source_id}-${src.field_path}-${j}`} type="button" onClick={() => focusSource(src.source_id, src.field_path)} aria-haspopup="dialog" className="inline-flex min-h-11 max-w-full items-center gap-2 break-words rounded-[var(--radius-control)] border border-edge bg-surface px-3 py-2 text-left text-xs font-medium text-accent shadow-rest hover:shadow-raised"><span aria-hidden="true">⧉</span>{strings.casePage.sourcePrefix}: {src.label_bn} → {src.value_bn || src.printed_text || src.field_path}</button>)}</div>
  );
  const review = assessment?.review_needed ?? [];
  const results = !assessment ? (
    step.status === "locked" || step.status === "waiting" ? gate(step) : (
      <div className="space-y-3 rounded-[var(--radius-card)] border border-line bg-surface p-5">
        <p className="text-sm text-muted">{strings.casePage.noAssessment}</p>
        <button type="button" onClick={runAssessment} disabled={assessing} className={primary}>{assessing ? strings.casePage.loadingAssessment : strings.casePage.verify}</button>
      </div>
    )
  ) : (
    <div className="space-y-5">
      {step.status === "action" && notice(step, caseView.assessment_stale ? undefined : 2, caseView.assessment_stale ? <button type="button" onClick={runAssessment} disabled={assessing} className={primary}>{assessing ? strings.casePage.loadingAssessment : strings.casePage.retryAssessment}</button> : undefined)}
      <div id="risk-summary" className="space-y-3">
        <VerdictBox riskLevel={riskBadge(assessment.risk_level, !reasons.length)} title={assessment.headline_bn} summary={assessment.summary_bn} reasons={reasons} />
        <SampleCompare landId={landId} risk={assessment.risk_level} ruleIds={(assessment.findings ?? []).map((f) => f.rule_id)} />
        <p className="text-xs text-muted">
          {assessmentDiff?.previous ? <>{riskName(assessmentDiff.previous.risk_level)} → {riskName(assessmentDiff.risk_level)}{en ? ". " : "। "}{assessmentDiff.added_findings.length ? `${strings.casePage.diffAdded}: ${assessmentDiff.added_findings.join(", ")}. ` : ""}{assessmentDiff.removed_findings.length ? `${strings.casePage.diffRemoved}: ${assessmentDiff.removed_findings.join(", ")}.` : ""}{!assessmentDiff.added_findings.length && !assessmentDiff.removed_findings.length ? strings.casePage.diffSame : ""}</> : strings.casePage.diffFirst}
        </p>
        {!caseView.assessment_stale && <button type="button" onClick={runAssessment} disabled={assessing} className={ghost}>{assessing ? strings.casePage.loadingAssessment : strings.casePage.retryAssessment}</button>}
      </div>
      <section data-tour="findings" className="space-y-3"><h3 className="font-heading text-lg font-bold text-ink">{strings.casePage.findingsHeading}</h3>
        {(assessment.findings ?? []).length ? (assessment.findings ?? []).map((finding, i) => <FindingCard key={`${finding.rule_id}-${i}`} tone={findingTone(finding.status)} title={finding.title_bn}><p className="text-sm leading-relaxed">{finding.message_bn}</p>{sourceButtons(finding.sources)}</FindingCard>)
          : <p className="rounded-xl border border-line bg-surface p-4 text-sm text-muted">{reasons.length ? t("যা মেলানো গেছে তাতে অমিল পাওয়া যায়নি; তবে নিচের অংশগুলো মেলানো যায়নি।", "No mismatch in what could be checked; the parts below could not be checked.") : strings.casePage.noFindings}</p>}
      </section>
      {toVerify.length > 0 && (
        <section className="space-y-3"><h3 className="font-heading text-lg font-bold text-ink">{t("যাচাই করা যায়নি / মিলিয়ে নিন", "Could not be checked / check by hand")}</h3>
          <p className="text-sm text-muted">{t("এই হিসাবগুলো OCR দিয়ে পড়া সংখ্যার ওপর; তাই অমিল হিসেবে ধরা হয়নি, ঝুঁকির মাত্রাও বাড়ায়নি।", "These rely on numbers read by OCR, so they are not counted as mismatches and do not raise the risk level.")}</p>
          {toVerify.map((item, i) => <FindingCard key={`${item.rule_id}-ocr-${i}`} tone="info" title={String(item.values?.ocr_original_title ?? item.title_bn)}><p className="text-sm leading-relaxed">{item.message_bn}</p>{sourceButtons(item.sources)}</FindingCard>)}
        </section>
      )}
      <section className="space-y-3"><h3 className="font-heading text-lg font-bold text-ink">{strings.casePage.passedHeading}</h3>
        {(expandedPassed ? assessment.passed ?? [] : (assessment.passed ?? []).slice(0, 3)).map((item, i) => <CheckItem key={`${item.rule_id}-${i}`} status="ok" title={item.title_bn} description={item.message_bn} />)}
        {!(assessment.passed ?? []).length && <p className="text-sm text-muted">{strings.casePage.noPassed}</p>}
        {(assessment.passed ?? []).length > 3 && <button type="button" onClick={() => setExpandedPassed((x) => !x)} className="min-h-11 px-2 text-sm text-accent underline">{expandedPassed ? strings.casePage.showLess : strings.casePage.showAll}</button>}
      </section>
      {(skippedReasons.length > 0 || review.length > 0) && (
        <section className="space-y-3 rounded-[var(--radius-card)] border border-line bg-surface p-4">
          <h3 className="font-heading text-lg font-bold text-ink">{t("যা মেলানো যায়নি: বিস্তারিত", "What could not be checked: details")}</h3>
          {skippedReasons.length > 0 && <ul className="list-disc space-y-1 pl-5 text-sm leading-6 text-muted">{skippedReasons.map((r) => <li key={r}>{r}</li>)}</ul>}
          {(assessment.coverage.documents_missing_bn ?? []).length > 0 && <Link href={`/upload/${landId}`} className={ghost}>{strings.casePage.uploadMissing}</Link>}
          {review.length > 0 && <>
            <p className="text-sm font-semibold text-ink">{t("এই ঘরগুলো নিজে মিলিয়ে নিন (পড়া নিয়ে সন্দেহ আছে):", "Check these fields yourself (the reading is uncertain):")}</p>
            {review.map((item, i) => <button key={`${item.source_id}-${item.field_path}-${i}`} type="button" onClick={() => focusSource(item.source_id, item.field_path)} aria-haspopup="dialog" className="block min-h-11 w-full rounded-[var(--radius-control)] border border-warn/30 bg-warn-bg/40 p-3 text-left text-sm">{item.document_label_bn} → {item.label_bn}: {item.printed_text || "—"}</button>)}
          </>}
        </section>
      )}
    </div>
  );

  const paperPanel = (
    <div className="space-y-4">
      <div role="tablist" aria-label={t("কাগজ যাচাইয়ের অংশ", "Parts of the paper check")} className="flex gap-1 overflow-x-auto rounded-[var(--radius-control)] bg-bg p-1">
        {([["results", "ফলাফল", "Results"], ["timeline", "মালিকানার ইতিহাস", "Ownership history"], ["deeds", "আগের দলিল", "Earlier deeds"]] as const).map(([key, bn, enLabel]) => (
          <button key={key} type="button" role="tab" aria-selected={paperTab === key} onClick={() => setPaperTab(key)}
            className={`min-h-11 flex-1 whitespace-nowrap rounded-md px-3 text-sm font-semibold ${paperTab === key ? "bg-surface text-accent shadow-rest" : "text-muted hover:text-ink"}`}>{en ? enLabel : bn}</button>
        ))}
      </div>
      {paperTab === "results" && results}
      {paperTab === "timeline" && <OwnershipTimeline id={landId} embedded />}
      {paperTab === "deeds" && <DeedArchive landId={landId} items={deedArchive} onOpenSource={(id) => openSource(id, null)} />}
    </div>
  );

  const limits = [
    t("কাগজে সব মিললেও মামলা, দখল বা বন্ধক কাগজে ধরা পড়ে না।", "Even if every paper matches, cases, possession or mortgages do not show on paper."),
    t("দলিল আসল না জাল, তা এই অ্যাপ প্রমাণ করে না; সাব-রেজিস্ট্রি অফিসের সার্টিফাইড কপি দেখুন।", "This app does not prove a deed is genuine; see the certified copy from the sub-registry office."),
    t("স্যাটেলাইট ফল প্লটের চারপাশের প্রায় ২০০ মিটার এলাকার; তা কাগজের ঝুঁকির মাত্রা বদলায় না।", "Satellite results cover about 200 m around the plot; they do not change the paper risk level."),
  ];
  const disclaimer = (!en && assessment?.disclaimer_bn) || strings.app.disclaimer;

  const panels: Record<number, React.ReactNode> = {
    1: (
      <div className="space-y-4">
        <dl className="grid grid-cols-2 gap-3 rounded-[var(--radius-card)] border border-edge bg-surface p-4 text-sm sm:grid-cols-5">
          {([["জেলা", "District", caseView.land.district], ["উপজেলা", "Upazila", caseView.land.upazila], ["মৌজা", "Mouza", caseView.land.mouza], ["দাগ", "Dag", caseView.land.dag_no], ["খতিয়ান", "Khatian", caseView.land.khatian_no]] as const).map(([bn, enLabel, v]) => (
            <div key={bn}><dt className="text-xs text-muted">{en ? enLabel : bn}</dt><dd className="font-semibold text-ink">{v ? num(v) : "—"}</dd></div>
          ))}
        </dl>
        {!geometry && <p className="rounded-[var(--radius-control)] border border-dashed border-line bg-bg/60 p-3 text-sm text-muted">{t("মানচিত্রের ডান দিকের বহুভুজ বোতাম চাপুন, প্লটের প্রতিটি কোণে ক্লিক করুন, শেষে “সীমানা রাখুন” চাপুন।", "Press the polygon button on the right of the map, click each corner of the plot, then press “Save boundary”.")}</p>}
        <div className="-mx-4 sm:mx-0"><PlotMap landId={landId} geometry={geometry} onSaved={() => { toast("ok", t("সীমানা রাখা হয়েছে।", "Boundary saved.")); void fetchData(); }} /></div>
        {geometry && <button type="button" onClick={() => goTo(4)} className={primary}>{t("ধাপ ৪: মাটি যাচাই →", "Step 4: ground check →")}</button>}
      </div>
    ),
    2: docsPanel,
    3: paperPanel,
    4: step.status === "locked" ? gate(step) : <SatellitePanel landId={landId} geometry={geometry} mapless onChecked={fetchData} />,
    5: step.status === "locked" || !assessment ? gate(step) : (
      <div className="space-y-4">
        <VerdictBox riskLevel={riskBadge(assessment.risk_level, !reasons.length)} title={assessment.headline_bn} summary={assessment.summary_bn} reasons={reasons} />
        {steps[3].status !== "done" && notice(steps[3], 4)}
        <button type="button" onClick={() => api.downloadReport(landId, assessment.id).catch((e) => toast("bad", e.message))} className={primary}>{strings.casePage.pdfReport}</button>
        <section className="rounded-[var(--radius-card)] border border-line bg-surface p-4">
          <h3 className="font-heading text-lg font-bold text-ink">{t("যা এই অ্যাপ বলে না", "What this app does not tell you")}</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-ink">{limits.map((l) => <li key={l}>{l}</li>)}</ul>
          <p className="mt-3 text-sm leading-6 text-muted">{disclaimer}</p>
          <Link href="/how-it-works#limits" className="mt-2 inline-flex min-h-11 items-center text-sm font-semibold text-accent underline underline-offset-4">{t("আরো জানুন", "Learn more")} →</Link>
        </section>
      </div>
    ),
    6: (
      <div className="space-y-4">
        <SellerIdentityPanel landId={landId} sellers={sellerRows} verifications={caseView.identity_verifications || []} />
        <Link href="/profile" className={ghost}>{t("নিজের (ক্রেতার) পরিচয় যাচাই", "Verify your own (buyer) identity")} →</Link>
      </div>
    ),
    7: (
      <div className="space-y-4">
        {steps[2].status !== "done" && notice(steps[2], 3)}
        <EscrowExplainer />
        {caseView.journey.escrow_deal_id
          ? <Link href={`/escrow/${caseView.journey.escrow_deal_id}`} className={primary}>{t("এসক্রো চুক্তি দেখুন", "Open the escrow deal")} →</Link>
          : <button type="button" onClick={startEscrow} disabled={escrowBusy} className={primary}>{escrowBusy ? strings.labels.loading : escrowFlow.start}</button>}
      </div>
    ),
    8: (
      <div className="space-y-3 rounded-[var(--radius-card)] border border-line bg-surface p-4 text-sm leading-6">
        <p className="text-ink">{step.status === "done" ? t("এই জমির খতিয়ান নজরদারিতে আছে।", "This plot's khatian is under watch.") : t("জমি কেনার পরে খতিয়ানের একটি কপি রাখুন; প্রতি মাসে নতুন কপি upload করলে বদল জানানো হবে।", "After buying, keep a copy of the khatian; upload a new copy each month to be told about changes.")}</p>
        <Link href="/guardian" className={primary}>{step.status === "done" ? t("নজরদারি দেখুন", "Open the watch") : t("নজরদারিতে রাখুন", "Put under watch")} →</Link>
      </div>
    ),
  };

  const label = STEP_LABELS[step.key as StepKey];
  return (
    <div className="mx-auto max-w-6xl space-y-5 py-4">
      <CaseHeader caseView={caseView} />
      <JourneyStepper steps={steps} active={active} onSelect={goTo} />
      <NextActions caseView={caseView} check={check} busyId={actionBusy} onToggle={updateAction} onGoToStep={goTo} />
      {confirmDialog}
      <Modal
        wide
        open={!!sourceDoc}
        onClose={() => setSourceView(null)}
        title={sourceDoc ? `${strings.casePage.sourcePrefix}: ${sourceDoc.label_bn}` : ""}
        description={t("নথির ছবি আর পড়া তথ্য পাশাপাশি; চিহ্নিত ঘরটি এই অমিলের উৎস।", "The document image and the data read from it, side by side; the marked field is the source of this mismatch.")}
        footer={<button type="button" onClick={() => setSourceView(null)} className={ghost}>{strings.buttons.close}</button>}
      >
        {sourceDoc && <DocumentFieldsPanel key={`modal-${sourceDoc.id}`} document={sourceDoc} fieldMetaList={metaFor(sourceDoc.doc_type)} onExtractionUpdated={fetchData} highlightField={highlightField} />}
      </Modal>
      {error && <div role="alert" className="rounded-xl border border-bad/40 bg-bad-bg p-3 text-sm">{error}</div>}
      <section id="step-panel" aria-labelledby="step-title" className="scroll-mt-[calc(var(--header-h,0px)+5rem)] space-y-4">
        <header className="space-y-1">
          <h2 id="step-title" className="font-heading text-2xl font-bold text-ink">{t("ধাপ", "Step")} {num(step.n)}: {en ? label.en : label.bn}</h2>
          <p className="text-sm leading-6 text-muted">{en ? PURPOSE[step.key as StepKey][1] : PURPOSE[step.key as StepKey][0]}</p>
        </header>
        {panels[active]}
      </section>
      {active !== 5 && <p className="rounded-xl border border-line bg-surface p-4 text-xs leading-relaxed text-muted"><strong className="block text-ink">{strings.casePage.disclaimerTitle}</strong>{disclaimer}</p>}
    </div>
  );
}
