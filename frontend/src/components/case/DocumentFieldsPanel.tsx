"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import { DocumentImageViewer } from "./DocumentImageViewer";
import { FieldRow } from "./FieldRow";
import { DocumentHistoryModal } from "./DocumentHistoryModal";
import {
  api,
  ApiError,
  CaseViewDocOut,
  CaseViewExtractionOut,
  EditItem,
  FieldMeta,
} from "@/lib/api";
import { strings } from "@/lib/strings";
import { Spinner } from "@/components/ui/Spinner";

interface DocumentFieldsPanelProps {
  document: CaseViewDocOut;
  fieldMetaList: FieldMeta[];
  onExtractionUpdated: (docId: string, newExtraction: CaseViewExtractionOut) => void;
}

export function DocumentFieldsPanel({
  document: doc,
  fieldMetaList,
  onExtractionUpdated,
}: DocumentFieldsPanelProps) {
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [filterNeedsReview, setFilterNeedsReview] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  // Edit states
  const [pendingEdits, setPendingEdits] = useState<Map<string, unknown>>(new Map());
  const [pendingRemovals, setPendingRemovals] = useState<Set<string>>(new Set());
  const [pendingAdditions, setPendingAdditions] = useState<Array<{ listName: string; value: Record<string, unknown> }>>([]);
  const [pendingConfirms, setPendingConfirms] = useState<Set<string>>(new Set());

  const [saving, setSaving] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Fetch presigned URL
  useEffect(() => {
    let active = true;
    api
      .getDocumentFile(doc.id)
      .then((res) => {
        if (active) setFileUrl(res.url);
      })
      .catch(() => {
        // Fallback or leave null
      });
    return () => {
      active = false;
    };
  }, [doc.id]);

  const latest = doc.latest_extraction;
  const data = (latest?.data as Record<string, unknown>) || {};
  const fieldFlags = (latest?.field_flags as Record<string, string[] | string>) || {};

  // Map of metadata by path pattern (e.g. "owners[].name" -> FieldMeta)
  const metaMap = useMemo(() => {
    const map = new Map<string, FieldMeta>();
    for (const f of fieldMetaList) {
      map.set(f.path, f);
    }
    return map;
  }, [fieldMetaList]);

  const getFieldMeta = (path: string): FieldMeta | undefined => {
    if (metaMap.has(path)) return metaMap.get(path);
    // Replace indices with []
    const normalized = path.replace(/\[\d+\]/g, "[]");
    return metaMap.get(normalized);
  };

  const handleFieldConfirm = useCallback((path: string) => {
    setPendingConfirms((prev) => new Set(prev).add(path));
    setSaveSuccess(false);
  }, []);

  const handleFieldEdit = useCallback((path: string, newValue: unknown) => {
    setPendingEdits((prev) => new Map(prev).set(path, newValue));
    setSaveSuccess(false);
  }, []);

  const handleRemoveRow = useCallback((rowPath: string) => {
    setPendingRemovals((prev) => new Set(prev).add(rowPath));
    setSaveSuccess(false);
  }, []);

  const handleAddRow = useCallback((listName: string) => {
    setPendingAdditions((prev) => [...prev, { listName, value: {} }]);
    setSaveSuccess(false);
  }, []);

  const isFieldNeedsReview = useCallback(
    (path: string, flags?: string[] | string) => {
      if (pendingConfirms.has(path) || pendingEdits.has(path)) return false;
      const fList = Array.isArray(flags)
        ? flags
        : typeof flags === "string"
          ? [flags]
          : [];
      return fList.some((f) => ["low", "medium"].includes(f.toLowerCase()));
    },
    [pendingConfirms, pendingEdits]
  );

  const handleSaveAll = async () => {
    setSaving(true);
    setServerError(null);
    setSaveSuccess(false);

    try {
      const edits: EditItem[] = [];

      // Removals
      for (const remPath of pendingRemovals) {
        edits.push({ field_path: remPath, remove: true });
      }

      // Value edits
      for (const [ePath, val] of pendingEdits.entries()) {
        edits.push({ field_path: ePath, value: val, remove: false });
      }

      // Additions
      for (const add of pendingAdditions) {
        edits.push({
          field_path: `${add.listName}[+]`,
          value: add.value,
          remove: false,
        });
      }

      const confirms = Array.from(pendingConfirms);

      const res = await api.patchDocumentExtraction(doc.id, {
        edits,
        confirms,
      });

      // Clear pending
      setPendingEdits(new Map());
      setPendingRemovals(new Set());
      setPendingAdditions([]);
      setPendingConfirms(new Set());
      setSaveSuccess(true);

      onExtractionUpdated(doc.id, res as CaseViewExtractionOut);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setServerError(err.message);
      } else {
        setServerError("তথ্য সংরক্ষণ করতে সমস্যা হয়েছে। অনুগ্রহ করে আবার চেষ্টা করুন।");
      }
    } finally {
      setSaving(false);
    }
  };

  const hasPendingChanges =
    pendingEdits.size > 0 ||
    pendingRemovals.size > 0 ||
    pendingAdditions.length > 0 ||
    pendingConfirms.size > 0;

  // Helper to extract nested value
  const getValueByPath = (obj: Record<string, unknown>, path: string): unknown => {
    if (pendingEdits.has(path)) {
      return pendingEdits.get(path);
    }
    const parts = path.split(".");
    let curr: unknown = obj;
    for (const part of parts) {
      if (curr === null || curr === undefined || typeof curr !== "object") return undefined;
      const m = part.match(/^(\w+)\[(\d+)\]$/);
      if (m) {
        const key = m[1];
        const idx = parseInt(m[2], 10);
        const list = (curr as Record<string, unknown>)[key];
        if (!Array.isArray(list) || idx >= list.length) return undefined;
        curr = list[idx];
      } else {
        curr = (curr as Record<string, unknown>)[part];
      }
    }
    return curr;
  };

  // Render a scalar or single nested field
  const renderField = (path: string, derivedPath?: string) => {
    const meta = getFieldMeta(path);
    if (!meta) return null;

    const val = getValueByPath(data, path);
    const derivedVal = derivedPath ? getValueByPath(data, derivedPath) : undefined;
    const flags = fieldFlags[path];

    if (filterNeedsReview && !isFieldNeedsReview(path, flags)) {
      return null;
    }

    return (
      <FieldRow
        key={path}
        path={path}
        labelBn={meta.label_bn}
        value={val}
        derivedValue={derivedVal}
        flags={flags}
        editable={meta.editable}
        enumOptions={meta.enum_options}
        isConfirmed={pendingConfirms.has(path)}
        isEdited={pendingEdits.has(path)}
        onConfirm={handleFieldConfirm}
        onEdit={handleFieldEdit}
      />
    );
  };

  // Render a list of items (owners, plots, etc.)
  const renderList = (
    listName: string,
    itemLabelPrefix: string,
    childFields: Array<{ name: string; derivedName?: string }>
  ) => {
    const rawList = (data[listName] as Array<Record<string, unknown>>) || [];
    const meta = metaMap.get(listName);

    return (
      <div key={listName} className="space-y-3 pt-2">
        <div className="flex items-center justify-between border-b border-line pb-1.5">
          <span className="text-sm font-bold font-heading text-ink">
            {meta?.label_bn || listName}
          </span>
          <button
            type="button"
            onClick={() => handleAddRow(listName)}
            className="text-xs font-semibold text-accent hover:underline flex items-center gap-1 min-h-[36px] px-2"
          >
            {strings.casePage.addRow}
          </button>
        </div>

        {rawList.map((item, idx) => {
          const rowPath = `${listName}[${idx}]`;
          if (pendingRemovals.has(rowPath)) {
            return null;
          }

          return (
            <div
              key={idx}
              className="p-3 rounded-xl border border-line bg-bg/30 space-y-2.5"
            >
              <div className="flex items-center justify-between border-b border-line/60 pb-1">
                <span className="text-xs font-bold font-heading text-ink">
                  {itemLabelPrefix} {idx + 1}
                </span>
                <button
                  type="button"
                  onClick={() => handleRemoveRow(rowPath)}
                  className="text-xs text-bad hover:underline font-medium min-h-[36px] px-2"
                >
                  {strings.casePage.removeRow}
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {childFields.map((cf) => {
                  const fPath = `${rowPath}.${cf.name}`;
                  const dPath = cf.derivedName ? `${rowPath}.${cf.derivedName}` : undefined;
                  return renderField(fPath, dPath);
                })}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  // Grouping fields per doc_type as specified in fields.md
  const docType = doc.doc_type || "khatian";

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
      {/* Left: Original Document Image/PDF with Zoom & Pan */}
      <div className="lg:col-span-5 w-full">
        <DocumentImageViewer fileUrl={fileUrl} filename={doc.original_filename} />
      </div>

      {/* Right: Extracted Fields, Highlighting, and Inline Editing */}
      <div className="lg:col-span-7 space-y-4">
        {/* Controls bar */}
        <div className="flex flex-wrap items-center justify-between gap-2 p-3 bg-surface border border-line rounded-xl">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setFilterNeedsReview(!filterNeedsReview)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg border transition-colors flex items-center gap-1.5 min-h-[44px] ${
                filterNeedsReview
                  ? "bg-warn-bg text-warn border-warn/40"
                  : "bg-surface text-ink border-line hover:bg-bg"
              }`}
            >
              <span>{filterNeedsReview ? "✓" : "○"}</span>
              <span>{strings.casePage.filterNeedsReview}</span>
            </button>
          </div>

          <button
            type="button"
            onClick={() => setIsHistoryOpen(true)}
            className="text-xs text-accent hover:underline font-medium px-2 py-1 min-h-[44px] flex items-center"
          >
            {strings.casePage.historyLink} →
          </button>
        </div>

        {serverError && (
          <div className="p-3 text-xs rounded-lg bg-bad-bg/60 border border-bad/30 text-bad font-medium">
            {serverError}
          </div>
        )}

        {saveSuccess && (
          <div className="p-3 text-xs rounded-lg bg-ok-bg/60 border border-ok/30 text-ok font-medium">
            ✓ {strings.casePage.saveSuccess}
          </div>
        )}

        {/* Fields list based on document type */}
        <div className="space-y-4 bg-surface p-4 rounded-xl border border-line">
          {docType === "khatian" && (
            <>
              {/* Identity & Location */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold font-heading text-muted uppercase tracking-wider">
                  জরিপ ও এলাকা
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {renderField("survey_type")}
                  {renderField("khatian_no")}
                  {renderField("location.district")}
                  {renderField("location.upazila")}
                  {renderField("location.mouza")}
                  {renderField("location.jl_no")}
                  {renderField("touzi_no")}
                  {renderField("record_date_text")}
                </div>
              </div>

              {/* Owners */}
              {renderList("owners", "মালিক", [
                { name: "name", derivedName: "name_normalized" },
                { name: "father_or_husband_name" },
                { name: "relation_marker" },
                { name: "share_text", derivedName: "share_shatangsho" },
                { name: "address_text" },
              ])}

              {/* Plots */}
              {renderList("plots", "দাগ", [
                { name: "dag_no" },
                { name: "land_class" },
                { name: "area_text", derivedName: "area_shatangsho" },
                { name: "plot_total_area_text", derivedName: "plot_total_area_shatangsho" },
                { name: "khatian_share_text", derivedName: "khatian_share_fraction" },
              ])}

              {/* Totals */}
              <div className="space-y-2 pt-2 border-t border-line">
                <h4 className="text-xs font-bold font-heading text-muted uppercase tracking-wider">
                  মোট জমি ও অন্যান্য
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {renderField("total_area_text", "total_area_shatangsho")}
                  {renderField("area_unit_text")}
                  {renderField("annual_revenue_text")}
                  {renderField("mutation_case_ref")}
                  {renderField("landlord_name")}
                </div>
              </div>
            </>
          )}

          {docType === "deed" && (
            <>
              <div className="space-y-2">
                <h4 className="text-xs font-bold font-heading text-muted uppercase tracking-wider">
                  দলিলের বিবরণ
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {renderField("deed_type")}
                  {renderField("is_draft")}
                  {renderField("deed_no")}
                  {renderField("deed_year")}
                  {renderField("registration_date_text")}
                  {renderField("sub_registry_office")}
                  {renderField("book_no")}
                </div>
              </div>

              {renderList("sellers", "বিক্রেতা", [
                { name: "name", derivedName: "name_normalized" },
                { name: "father_or_husband_name" },
                { name: "relation_marker" },
                { name: "share_text" },
                { name: "address_text" },
              ])}

              {renderList("buyers", "ক্রেতা", [
                { name: "name", derivedName: "name_normalized" },
                { name: "father_or_husband_name" },
                { name: "relation_marker" },
                { name: "share_text" },
                { name: "address_text" },
              ])}

              <div className="space-y-2 pt-2 border-t border-line">
                <h4 className="text-xs font-bold font-heading text-muted uppercase tracking-wider">
                  তফসিল ও হস্তান্তর
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {renderField("schedule_location.district")}
                  {renderField("schedule_location.upazila")}
                  {renderField("schedule_location.mouza")}
                  {renderField("schedule_location.jl_no")}
                  {renderField("transferred_area_text", "transferred_area_shatangsho")}
                  {renderField("price_taka")}
                  {renderField("price_text")}
                  {renderField("title_source_text")}
                </div>
              </div>

              {renderList("schedule_plots", "তফসিল দাগ", [
                { name: "dag_no" },
                { name: "land_class" },
                { name: "area_text", derivedName: "area_shatangsho" },
                { name: "plot_total_area_text" },
              ])}

              {renderList("schedule_khatians", "তফসিল খতিয়ান", [
                { name: "survey_type" },
                { name: "khatian_no" },
              ])}

              {renderList("prior_deeds", "বায়া দলিল", [
                { name: "deed_no" },
                { name: "deed_year" },
              ])}
            </>
          )}

          {docType === "dcr" && (
            <>
              <div className="space-y-2">
                <h4 className="text-xs font-bold font-heading text-muted uppercase tracking-wider">
                  নামজারি আদেশ ও খতিয়ান
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {renderField("case_no")}
                  {renderField("office")}
                  {renderField("order_date_text")}
                  {renderField("new_khatian_no")}
                  {renderField("old_khatian_no")}
                  {renderField("holding_no")}
                  {renderField("basis_text")}
                </div>
              </div>

              <div className="space-y-2 pt-2 border-t border-line">
                <h4 className="text-xs font-bold font-heading text-muted uppercase tracking-wider">
                  ডি.সি.আর. ও এলাকা
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {renderField("dcr_no")}
                  {renderField("fee_taka")}
                  {renderField("location.district")}
                  {renderField("location.upazila")}
                  {renderField("location.mouza")}
                  {renderField("location.jl_no")}
                </div>
              </div>

              {renderList("owners", "মালিক", [
                { name: "name", derivedName: "name_normalized" },
                { name: "father_or_husband_name" },
                { name: "relation_marker" },
                { name: "share_text", derivedName: "share_shatangsho" },
                { name: "address_text" },
              ])}

              {renderList("plots", "দাগ", [
                { name: "dag_no" },
                { name: "land_class" },
                { name: "area_text", derivedName: "area_shatangsho" },
              ])}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-2 border-t border-line">
                {renderField("total_area_text", "total_area_shatangsho")}
                {renderField("area_unit_text")}
              </div>
            </>
          )}

          {docType === "heir_cert" && (
            <>
              <div className="space-y-2">
                <h4 className="text-xs font-bold font-heading text-muted uppercase tracking-wider">
                  সনদ ও মৃত ব্যক্তির বিবরণ
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {renderField("certificate_no")}
                  {renderField("issuing_authority")}
                  {renderField("issuer_title")}
                  {renderField("deceased_name")}
                  {renderField("deceased_father_or_husband_name")}
                  {renderField("date_of_death_text")}
                  {renderField("deceased_address.district")}
                  {renderField("deceased_address.upazila")}
                  {renderField("deceased_address.mouza")}
                  {renderField("deceased_address.address_text")}
                </div>
              </div>

              {renderList("heirs", "ওয়ারিশ", [
                { name: "name", derivedName: "name_normalized" },
                { name: "father_or_husband_name" },
                { name: "relation" },
                { name: "relation_text" },
                { name: "is_deceased" },
                { name: "share_text", derivedName: "share_fraction" },
              ])}
            </>
          )}
        </div>

        {/* Save button bar */}
        <div className="flex items-center justify-between p-4 bg-surface border border-line rounded-xl sticky bottom-4 shadow-md">
          <div className="text-xs text-muted">
            {hasPendingChanges
              ? "পরিবর্তন বা নিশ্চিতকরণগুলো সংরক্ষণ করতে বোতাম চাপুন"
              : "সব তথ্য যাচাইকৃত"}
          </div>
          <button
            type="button"
            disabled={!hasPendingChanges || saving}
            onClick={handleSaveAll}
            className="px-5 py-2.5 rounded-lg bg-accent text-surface font-semibold text-sm hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 min-h-[44px]"
          >
            {saving ? (
              <>
                <Spinner size="sm" />
                <span>{strings.casePage.savingCorrections}</span>
              </>
            ) : (
              <span>{strings.casePage.saveAllCorrections}</span>
            )}
          </button>
        </div>
      </div>

      {/* History Modal */}
      <DocumentHistoryModal
        documentId={doc.id}
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
      />
    </div>
  );
}
