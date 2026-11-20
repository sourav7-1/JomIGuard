"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  api,
  AssessmentDiff,
  CaseViewDocOut,
  DeedArchiveItemOut,
  FieldsMetaResponse,
  FingerprintVerificationOut,
  LandCaseViewOut,
  PlotGeometry,
} from "@/lib/api";
import { SatellitePanel } from "@/components/case/SatellitePanel";
import { CaseTracker } from "@/components/case/CaseTracker";
import { strings } from "@/lib/strings";
import { CaseSkeleton } from "@/components/ui/Skeleton";
import { Modal, useConfirm } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";
import { EmptyState } from "@/components/ui/EmptyState";
import { VerdictBox } from "@/components/ui/VerdictBox";
import { CheckItem } from "@/components/ui/CheckItem";
import { Card } from "@/components/ui/Card";
import { FindingCard, findingTone } from "@/components/ui/FindingCard";
import {
  CaseHeader,
  CaseSummaryTable,
  DocumentFieldsPanel,
} from "@/components/case";
import { SellerIdentityPanel } from "@/components/case/SellerIdentityPanel";
import { escrowFlow } from "@/lib/strings";

interface CaseDetailClientProps {
  landId: string;
  source?: string;
  field?: string;
}

function archiveValue(value: unknown): string {
  if (value == null || value === "") return "—";
  if (Array.isArray(value)) {
    return value.map((item) => typeof item === "object" && item ? Object.values(item as Record<string, unknown>).filter(Boolean).join(" · ") : String(item)).join(", ") || "—";
  }
  if (typeof value === "object") return Object.values(value as Record<string, unknown>).filter(Boolean).join(" · ") || "—";
  return String(value);
}

const RISK_BN: Record<string, string> = { low: "কম ঝুঁকি", medium: "মাঝারি ঝুঁকি", high: "উচ্চ ঝুঁকি" };
const riskName = (level: string) => RISK_BN[level] ?? level;
// A rule's source field_path names a derived field; the document panel shows the printed one.
const printedField = (path: string) => path.replace(/name_normalized$/, "name").replace(/_(?:shatangsho|fraction)$/, "_text");

export function CaseDetailClient({ landId, source, field }: CaseDetailClientProps) {
  const router = useRouter();
  const [caseView, setCaseView] = useState<LandCaseViewOut | null>(null);
  const [deedArchive, setDeedArchive] = useState<DeedArchiveItemOut[]>([]);
  const [fingerprints, setFingerprints] = useState<Record<string, FingerprintVerificationOut>>({});
  const [fingerprintBusy, setFingerprintBusy] = useState<string | null>(null);
  const [fieldsMeta, setFieldsMeta] = useState<FieldsMetaResponse | null>(null);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [assessmentDiff, setAssessmentDiff] = useState<AssessmentDiff | null>(null);
  const [assessmentCount, setAssessmentCount] = useState(0);
  const [assessing, setAssessing] = useState(false);
  const [expandedPassed, setExpandedPassed] = useState(false);
  const [highlightField, setHighlightField] = useState<string | null>(null);
  const [actionBusy, setActionBusy] = useState<string | null>(null);
  const [escrowBusy, setEscrowBusy] = useState(false);
  // finding / timeline source viewer: the document page opens in a modal instead of scrolling away
  const [sourceView, setSourceView] = useState<{ docId: string; field: string | null } | null>(null);
  const toast = useToast();
  const { ask, dialog: confirmDialog } = useConfirm();

  const fetchData = useCallback(async () => {
    try {
      const [cv, meta, history, deeds] = await Promise.all([
        api.getLandCaseView(landId),
        api.getFieldsMeta(),
        api.getAssessments(landId),
        api.getLandDeeds(landId),
      ]);
      setCaseView(cv);
      setDeedArchive(deeds.items);
      setFieldsMeta(meta);
      setAssessmentCount(history.length);
      setAssessmentDiff(cv.latest_assessment ? await api.getAssessmentDiff(landId, cv.latest_assessment.id).catch(() => null) : null);

      if (cv.documents.length > 0) {
        setSelectedDocId((prev) => {
          if (prev && cv.documents.some((d) => d.id === prev)) {
            return prev;
          }
          return cv.documents[0].id;
        });
      }
    } catch {
      setError("কেসের তথ্য লোড করতে সমস্যা হয়েছে।");
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
      toast("ok", "নতুন করে মিলিয়ে দেখা হয়েছে।");
    } catch (e) {
      const msg = e instanceof Error ? e.message : strings.casePage.assessmentError;
      setError(msg);
      toast("bad", msg);
    } finally {
      setAssessing(false);
    }
  };

  const focusSource = (sourceId: string, fieldPath: string) => {
    openSource(sourceId, printedField(fieldPath));
  };

  const openSource = (docId: string, field: string | null) => {
    setHighlightField(field ? `${docId}:${field}` : null);
    setSourceView({ docId, field });
    if (field) window.setTimeout(() => document.querySelector(`dialog[open] [id="field-${docId}-${field}"]`)?.scrollIntoView({ behavior: "smooth", block: "center" }), 350);
  };

  const verifyCopy = async (documentId: string) => {
    setFingerprintBusy(documentId);
    try {
      const result = await api.verifyDocumentFingerprint(documentId);
      setFingerprints((current) => ({ ...current, [documentId]: result }));
    } catch (e) {
      setError(e instanceof Error ? e.message : strings.deedArchive.noBaseline);
      setFingerprints((current) => { const next = { ...current }; delete next[documentId]; return next; });
    } finally {
      setFingerprintBusy(null);
    }
  };

  const showArchiveSource = (documentId: string) => openSource(documentId, null);

  const updateAction = async (actionId: string, done: boolean) => {
    setActionBusy(actionId);
    try {
      await api.updateAction(landId, actionId, done);
      await fetchData();
      toast("ok", done ? "কাজটি শেষ হিসেবে রাখা হয়েছে।" : "কাজটি আবার খোলা হয়েছে।");
    } catch (e) {
      toast("bad", e instanceof Error ? e.message : strings.casePage.assessmentError);
    } finally {
      setActionBusy(null);
    }
  };

  const startEscrow = async () => {
    const ok = await ask({
      title: "বায়না escrow শুরু করবেন?",
      message: "এই কেসের জন্য একটি নমুনা বায়না escrow চুক্তির খসড়া তৈরি হবে। ডেমোতে ব্যাংক নমুনা; কোনো আসল টাকা জমা বা স্থানান্তর হয় না।",
      confirmLabel: "escrow শুরু করুন",
    });
    if (!ok) return;
    setEscrowBusy(true);
    try {
      const deal = await api.createEscrow(landId, {
        price: "6000000", bayna: "500000",
        deadline: new Date(Date.now() + 60 * 86400000).toISOString().slice(0, 10),
      });
      toast("ok", "escrow খসড়া তৈরি হয়েছে।");
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

  const handleExtractionUpdated = useCallback(
    () => {
      // Re-fetch to update staleness and document data cleanly
      fetchData();
    },
    [fetchData]
  );

  if (loading) {
    return <CaseSkeleton />;
  }

  if (error || !caseView) {
    return (
      <div className="max-w-2xl mx-auto py-12">
        <EmptyState
          title={strings.casePage.caseNotFound}
          description={error || strings.casePage.invalidCaseId}
          actionLabel={strings.casePage.startCheck}
          actionHref="/upload"
        />
        <p className="mt-5 rounded-xl border border-line bg-surface p-4 text-sm leading-relaxed text-muted"><strong className="block text-ink">{strings.casePage.disclaimerTitle}</strong>{strings.app.disclaimer}</p>
      </div>
    );
  }

  if (caseView.documents.length === 0) {
    return (
      <div className="max-w-3xl mx-auto py-6 space-y-6">
        <CaseHeader caseView={caseView} onAssessmentTriggered={fetchData} />
        <EmptyState
          title={strings.casePage.emptyDocList}
          description={strings.casePage.emptyDocDescription}
          actionLabel={strings.casePage.verify}
          actionHref={`/upload/${landId}`}
        />
        <p className="rounded-xl border border-line bg-surface p-4 text-sm leading-relaxed text-muted"><strong className="block text-ink">{strings.casePage.disclaimerTitle}</strong>{caseView.latest_assessment?.disclaimer_bn || strings.app.disclaimer}</p>
      </div>
    );
  }

  const selectedDoc =
    caseView.documents.find((d) => d.id === selectedDocId) || caseView.documents[0];

  const docType = selectedDoc?.doc_type || "khatian";
  const fieldMetaList = fieldsMeta ? (fieldsMeta as Record<string, typeof fieldsMeta.khatian>)[docType] || [] : [];
  const proposedDeed = caseView.documents.find((doc) => doc.role === "proposed_deed");
  const sellerRows = (proposedDeed?.latest_extraction?.data as { sellers?: { name: string }[] } | null)?.sellers || [];
  const sourceDoc = sourceView ? caseView.documents.find((d) => d.id === sourceView.docId) : undefined;
  const sourceMeta = sourceDoc && fieldsMeta ? (fieldsMeta as Record<string, typeof fieldsMeta.khatian>)[sourceDoc.doc_type || "khatian"] || [] : [];

  return (
    <div className="max-w-6xl mx-auto py-4 space-y-6">
      {/* 1. Header: title, stale banner & re-assess button */}
      <CaseHeader caseView={caseView} onAssessmentTriggered={fetchData} />
      <CaseTracker landId={landId} caseView={caseView} />
      {confirmDialog}
      <Modal
        wide
        open={!!sourceDoc}
        onClose={() => setSourceView(null)}
        title={sourceDoc ? `উৎস: ${sourceDoc.label_bn}` : ""}
        description="নথির ছবি আর পড়া তথ্য পাশাপাশি; চিহ্নিত ঘরটি এই অমিলের উৎস।"
        footer={<button type="button" onClick={() => setSourceView(null)} className="min-h-11 rounded-[var(--radius-control)] border border-line bg-surface px-4 text-sm font-semibold text-ink hover:bg-bg">বন্ধ করুন</button>}
      >
        {sourceDoc && <DocumentFieldsPanel key={`modal-${sourceDoc.id}`} document={sourceDoc} fieldMetaList={sourceMeta} onExtractionUpdated={handleExtractionUpdated} highlightField={highlightField} />}
      </Modal>
      {error && <div role="alert" className="rounded-xl border border-bad/40 bg-bad-bg p-3 text-sm">{error}</div>}
      {caseView.latest_assessment ? (() => {
        const assessment = caseView.latest_assessment;
        const findings = assessment.findings ?? [];
        const passed = assessment.passed ?? [];
        const actions = assessment.actions ?? [];
        const reviewNeeded = assessment.review_needed ?? [];
        const missingDocs = assessment.coverage.documents_missing_bn ?? [];
        const skippedChecks = assessment.coverage.checks_skipped ?? [];
        return <section id="risk-summary" className="scroll-mt-40 space-y-4">
          <VerdictBox riskLevel={assessment.risk_level as "low" | "medium" | "high"} title={assessment.headline_bn} summary={assessment.summary_bn} />
          <p className="rounded-lg border border-line bg-surface p-3 text-sm text-muted">
            {assessmentDiff?.previous ? <>{riskName(assessmentDiff.previous.risk_level)} → {riskName(assessmentDiff.risk_level)}। {assessmentDiff.added_findings.length ? `${strings.casePage.diffAdded}: ${assessmentDiff.added_findings.join(", ")}. ` : ""}{assessmentDiff.removed_findings.length ? `${strings.casePage.diffRemoved}: ${assessmentDiff.removed_findings.join(", ")}.` : ""}{!assessmentDiff.added_findings.length && !assessmentDiff.removed_findings.length ? strings.casePage.diffSame : ""}</> : strings.casePage.diffFirst}
          </p>
          <div className="flex flex-col sm:flex-row gap-2">
            <button type="button" onClick={runAssessment} disabled={assessing} className="min-h-11 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-60">{assessing ? strings.casePage.loadingAssessment : strings.casePage.retryAssessment}</button>
            <button type="button" onClick={() => api.downloadReport(landId, assessment.id).catch((e) => setError(e.message))} className="min-h-11 rounded-lg border border-line bg-surface px-4 py-2 text-sm font-semibold">{strings.casePage.pdfReport}</button>
          </div>
          <section className="space-y-3"><h2 className="font-heading text-xl font-bold text-ink">{strings.casePage.findingsHeading}</h2>
            {findings.length ? findings.map((finding, i) => <FindingCard key={`${finding.rule_id}-${i}`} tone={findingTone(finding.status)} title={finding.title_bn}><p className="text-sm leading-relaxed">{finding.message_bn}</p><div className="flex flex-wrap gap-2">{(finding.sources ?? []).map((source, j) => <button key={`${source.source_id}-${source.field_path}-${j}`} type="button" onClick={() => focusSource(source.source_id, source.field_path)} aria-haspopup="dialog" className="inline-flex min-h-11 max-w-full items-center gap-2 break-words rounded-[var(--radius-control)] border border-edge bg-surface px-3 py-2 text-left text-xs font-medium text-accent shadow-rest transition-shadow hover:shadow-raised"><span aria-hidden="true">⧉</span>{strings.casePage.sourcePrefix}: {source.label_bn} → {source.value_bn || source.printed_text || source.field_path}</button>)}</div></FindingCard>) : <p className="rounded-xl border border-line bg-surface p-4 text-sm text-muted">{strings.casePage.noFindings}</p>}
          </section>
          <section className="space-y-3"><h2 className="font-heading text-xl font-bold text-ink">{strings.casePage.passedHeading}</h2>
            {(expandedPassed ? passed : passed.slice(0, 3)).map((item, i) => <CheckItem key={`${item.rule_id}-${i}`} status="ok" title={item.title_bn} description={item.message_bn} />)}
            {!passed.length && <p className="text-sm text-muted">{strings.casePage.noPassed}</p>}
            {passed.length > 3 && <button type="button" onClick={() => setExpandedPassed((x) => !x)} className="min-h-11 px-2 text-sm text-accent underline">{expandedPassed ? strings.casePage.showLess : strings.casePage.showAll}</button>}
          </section>
          <section className="space-y-2 rounded-[var(--radius-card)] border border-line bg-surface p-4 shadow-[var(--shadow-card)]"><h2 className="font-heading text-xl font-bold text-ink">{strings.casePage.coverageHeading}</h2>
            {missingDocs.map((doc, i) => <p key={`${doc}-${i}`} className="text-sm text-muted">• {doc}</p>)}
            {skippedChecks.map((check, i) => <p key={`${check.rule_id}-${i}`} className="text-sm text-muted">• {check.reason_bn}</p>)}
            <Link href={`/upload/${landId}`} className="inline-flex min-h-11 items-center rounded-lg border border-line px-3 py-2 text-sm font-semibold text-accent">{strings.casePage.uploadMissing}</Link>
          </section>
          <section className="space-y-3"><h2 className="font-heading text-xl font-bold text-ink">{strings.casePage.reviewHeading}</h2>
            {reviewNeeded.length ? reviewNeeded.map((item, i) => <button key={`${item.source_id}-${item.field_path}-${i}`} type="button" onClick={() => focusSource(item.source_id, item.field_path)} aria-haspopup="dialog" className="lift block min-h-11 w-full rounded-[var(--radius-control)] border border-warn/30 bg-warn-bg/40 p-3 text-left text-sm shadow-rest">{item.document_label_bn} → {item.label_bn}: {item.printed_text || "—"}</button>) : <p className="text-sm text-muted">{strings.casePage.noReview}</p>}
          </section>
          <section className="space-y-3"><h2 id="actions-title" className="scroll-mt-40 font-heading text-xl font-bold text-ink">{strings.casePage.actionsHeading}</h2>
            {actions.length ? actions.map((action, i) => <label key={`${action.id}-${i}`} className="flex min-h-11 items-start gap-3 rounded-xl border border-line bg-surface p-3 text-sm"><input type="checkbox" checked={Boolean(action.done)} disabled={actionBusy === action.id} onChange={(e) => updateAction(action.id, e.target.checked)} className="mt-1 h-5 w-5 shrink-0 accent-accent"/><span className={`min-w-0 flex-1 leading-relaxed ${action.done ? "line-through text-muted" : "text-ink"}`}>{action.text_bn}<span className="ml-2 inline-flex rounded-full bg-bg px-2 py-0.5 text-xs text-muted">{strings.casePage.who[action.who as keyof typeof strings.casePage.who] || action.who}</span></span></label>) : <p className="text-sm text-muted">{strings.casePage.noActions}</p>}
          </section>
          <SellerIdentityPanel landId={landId} sellers={sellerRows} verifications={caseView.identity_verifications || []} />
          <button type="button" onClick={startEscrow} disabled={escrowBusy} className="min-h-11 rounded-lg border border-line bg-surface px-4 text-sm font-semibold text-accent">{escrowBusy ? strings.labels.loading : escrowFlow.start}</button>
        </section>;
      })() : <><SellerIdentityPanel landId={landId} sellers={sellerRows} verifications={caseView.identity_verifications || []} /><section className="space-y-3 rounded-xl border border-line bg-surface p-5"><h2 className="text-lg font-bold">{strings.casePage.findingsHeading}</h2><p className="text-sm text-muted">{assessmentCount ? strings.casePage.assessmentError : strings.casePage.noAssessment}</p><button type="button" onClick={runAssessment} disabled={assessing} className="min-h-11 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-60">{assessing ? strings.casePage.loadingAssessment : strings.casePage.verify}</button></section></>}
      <p className="rounded-xl border border-line bg-surface p-4 text-sm leading-relaxed text-muted"><strong className="block text-ink">{strings.casePage.disclaimerTitle}</strong>{caseView.latest_assessment?.disclaimer_bn || strings.app.disclaimer}</p>

      <SatellitePanel landId={landId} geometry={(caseView.land as { geometry?: PlotGeometry | null }).geometry ?? null} />

      <section className="space-y-3 rounded-xl border border-line bg-surface p-4 sm:p-5" aria-labelledby="deed-archive-title">
        <div className="space-y-1">
          <h2 id="deed-archive-title" className="font-heading text-xl font-bold text-ink">{strings.deedArchive.title}</h2>
          <Link href={`/cases/${landId}/deeds`} className="inline-flex min-h-11 items-center rounded-lg border border-line px-3 py-2 text-sm font-semibold text-accent">আগের দলিল ও প্রমাণ বিস্তারিত দেখুন</Link>
          <p className="text-sm leading-relaxed text-muted">{strings.deedArchive.description}</p>
          <p className="text-sm font-semibold text-warn">{strings.deedArchive.officialNotice}</p>
          <p className="text-xs leading-relaxed text-muted">{strings.deedArchive.authenticityLimit}</p>
        </div>
        <Link href={`/upload/${landId}`} className="inline-flex min-h-11 w-fit items-center rounded-lg border border-line px-3 py-2 text-sm font-semibold text-accent">{strings.deedArchive.add}</Link>
        {deedArchive.length ? <ol className="space-y-3">
          {deedArchive.map((deed: DeedArchiveItemOut, index) => {
            const check = fingerprints[deed.id];
            const busy = fingerprintBusy === deed.id;
            return <li key={deed.id} className="min-w-0 rounded-xl border border-line bg-bg/40 p-3 sm:p-4">
              <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0 space-y-1">
                  <h3 className="break-words font-semibold">{deed.data.deed_no ? `${strings.deedArchive.title} · ${deed.data.deed_no}` : deed.original_filename}</h3>
                  <p className="break-words text-sm text-muted">{deed.data.registration_date || deed.data.registration_date_text || deed.data.deed_year || "—"} · {deed.data.sellers.map((p) => p.name).join(", ")} → {deed.data.buyers.map((p) => p.name).join(", ")}</p>
                  <p className="break-all text-xs text-muted">{strings.deedArchive.uploadedAt}: {new Date(deed.created_at).toLocaleDateString("bn-BD")}{deed.uploaded_by ? ` · ${strings.deedArchive.uploadedBy}: ${deed.uploaded_by}` : ""}</p>
                </div>
                <button type="button" aria-haspopup="dialog" onClick={() => showArchiveSource(deed.id)} className="min-h-11 shrink-0 rounded-lg border border-line bg-surface px-3 py-2 text-left text-sm font-semibold text-accent">{strings.deedArchive.source}</button>
              </div>
              <p className="mt-2 break-all text-xs text-muted">{strings.deedArchive.fingerprint}: {deed.content_sha256 || strings.deedArchive.noBaseline}</p>
              <button type="button" onClick={() => verifyCopy(deed.id)} disabled={busy} className="mt-2 min-h-11 rounded-lg border border-line bg-surface px-3 py-2 text-sm font-semibold disabled:opacity-60">{busy ? strings.deedArchive.checking : strings.deedArchive.verifyCopy}</button>
              {check && <p role="status" className={`mt-2 text-sm ${check.unchanged_since_upload === false ? "text-bad" : "text-muted"}`}>
                {check.unchanged_since_upload === true ? strings.deedArchive.unchanged : check.unchanged_since_upload === false ? strings.deedArchive.changed : strings.deedArchive.noBaseline}
                <span className="block break-all text-xs">SHA-256: {check.current_sha256}</span>
              </p>}
              {index > 0 && <div className="mt-3 space-y-2 border-t border-line pt-3">
                <h4 className="text-sm font-semibold">{strings.deedArchive.comparison}</h4>
                <div className="space-y-2">{deed.comparison.map((field) => <div key={field.key} className="grid min-w-0 gap-1 rounded-lg bg-surface p-2 text-sm sm:grid-cols-[8rem_1fr_1fr]">
                  <strong className="break-words">{field.label_bn}</strong>
                  <span className="min-w-0 break-words"><span className="text-xs text-muted">{strings.deedArchive.previousValue}: </span>{archiveValue(field.previous)}</span>
                  <span className="min-w-0 break-words"><span className="text-xs text-muted">{strings.deedArchive.currentValue}: </span>{archiveValue(field.current)}</span>
                </div>)}</div>
              </div>}
            </li>;
          })}
        </ol> : <p className="rounded-lg bg-bg p-3 text-sm text-muted">{strings.deedArchive.empty}</p>}
      </section>

      {/* 3. Summary table: Land Case File */}
      <CaseSummaryTable
        documents={caseView.documents}
        selectedDocId={selectedDoc.id}
        onSelectDoc={setSelectedDocId}
      />

      {/* 4. Document selector tabs */}
      <div id="source-document-panel" className="space-y-3 scroll-mt-40">
        <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
          {caseView.documents.map((d: CaseViewDocOut) => {
            const isSelected = d.id === selectedDoc.id;
            return (
              <button
                key={d.id}
                type="button"
                onClick={() => setSelectedDocId(d.id)}
                className={`px-3.5 py-2 rounded-xl text-xs font-semibold whitespace-nowrap transition-colors flex items-center gap-1.5 min-h-[44px] border ${
                  isSelected
                    ? "bg-accent text-surface border-accent shadow-xs"
                    : "bg-surface text-ink border-line hover:bg-bg"
                }`}
              >
                <span>{d.label_bn}</span>
              </button>
            );
          })}
        </div>

        {/* 5. Document Panel: Image with Zoom/Pan next to Fields */}
        <DocumentFieldsPanel
          key={selectedDoc.id}
          document={selectedDoc}
          fieldMetaList={fieldMetaList}
          onExtractionUpdated={handleExtractionUpdated}
          highlightField={highlightField}
        />
      </div>

      {/* Link to Upload more docs */}
      <Card className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-bg/50">
        <div className="text-xs text-muted">
          আরো কোনো দলিল বা খতিয়ান যোগ করতে চান?
        </div>
        <Link
          href={`/upload/${landId}`}
          className="text-xs font-semibold text-accent hover:underline flex items-center gap-1 min-h-[44px] px-3 py-2 border border-line rounded-lg bg-surface self-start sm:self-auto"
        >
          + আরো কাগজ যোগ করুন
        </Link>
      </Card>
    </div>
  );
}
