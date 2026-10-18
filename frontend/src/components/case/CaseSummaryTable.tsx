"use client";

import React from "react";
import { CaseViewDocOut } from "@/lib/api";
import { strings } from "@/lib/strings";

interface CaseSummaryTableProps {
  documents: CaseViewDocOut[];
  selectedDocId?: string;
  onSelectDoc?: (docId: string) => void;
}

export function CaseSummaryTable({
  documents,
  selectedDocId,
  onSelectDoc,
}: CaseSummaryTableProps) {
  if (documents.length === 0) {
    return null;
  }

  const getDocData = (doc: CaseViewDocOut) => {
    const raw = (doc.latest_extraction?.data as Record<string, unknown>) || {};
    const docType = doc.doc_type;

    // Owners / Sellers
    let owners = "—";
    if (docType === "khatian" || docType === "dcr") {
      const list = (raw.owners as Array<{ name?: string }>) || [];
      if (list.length > 0) {
        owners = list.map((o) => o.name).filter(Boolean).join(", ");
      }
    } else if (docType === "deed") {
      const sellers = (raw.sellers as Array<{ name?: string }>) || [];
      if (sellers.length > 0) {
        owners = sellers.map((s) => s.name).filter(Boolean).join(", ");
      }
    } else if (docType === "heir_cert") {
      if (raw.deceased_name) {
        owners = `মৃত ${raw.deceased_name}`;
      }
    }

    // Dag
    let dag = "—";
    if (docType === "khatian" || docType === "dcr") {
      const plots = (raw.plots as Array<{ dag_no?: string }>) || [];
      if (plots.length > 0) {
        dag = plots.map((p) => p.dag_no).filter(Boolean).join(", ");
      }
    } else if (docType === "deed") {
      const plots = (raw.schedule_plots as Array<{ dag_no?: string }>) || [];
      if (plots.length > 0) {
        dag = plots.map((p) => p.dag_no).filter(Boolean).join(", ");
      }
    }

    // Khatian
    let khatian = "—";
    if (docType === "khatian") {
      khatian = `${raw.survey_type || ""} ${raw.khatian_no || ""}`.trim() || "—";
    } else if (docType === "deed") {
      const sk = (raw.schedule_khatians as Array<{ survey_type?: string; khatian_no?: string }>) || [];
      if (sk.length > 0) {
        khatian = sk.map((k) => `${k.survey_type || ""} ${k.khatian_no || ""}`.trim()).join(", ");
      }
    } else if (docType === "dcr") {
      khatian = String(raw.new_khatian_no || raw.old_khatian_no || "—");
    }

    // Area
    let area = "—";
    if (docType === "khatian" || docType === "dcr") {
      if (raw.total_area_shatangsho !== undefined && raw.total_area_shatangsho !== null) {
        area = raw.total_area_text ? `${raw.total_area_text} · ${raw.total_area_shatangsho} শতাংশ` : "—";
      }
    } else if (docType === "deed") {
      if (raw.transferred_area_shatangsho !== undefined && raw.transferred_area_shatangsho !== null) {
        area = raw.transferred_area_text ? `${raw.transferred_area_text} · ${raw.transferred_area_shatangsho} শতাংশ` : "—";
      }
    }

    return { owners, dag, khatian, area };
  };

  return (
    <div className="bg-surface rounded-xl border border-line shadow-xs overflow-hidden space-y-2 p-4">
      <h3 className="font-heading font-bold text-base text-ink flex items-center gap-2">
        <span>📑</span> {strings.casePage.summaryTableTitle}
      </h3>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm border-collapse min-w-[560px]">
          <thead>
            <tr className="border-b border-line bg-bg/50 text-muted font-heading text-xs">
              <th className="py-2.5 px-3">{strings.casePage.thDoc}</th>
              <th className="py-2.5 px-3">{strings.casePage.thOwnerSeller}</th>
              <th className="py-2.5 px-3 font-mono">{strings.casePage.thDag}</th>
              <th className="py-2.5 px-3 font-mono">{strings.casePage.thKhatian}</th>
              <th className="py-2.5 px-3 font-mono">{strings.casePage.thArea}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line/60">
            {documents.map((doc) => {
              const { owners, dag, khatian, area } = getDocData(doc);
              const isSelected = selectedDocId === doc.id;

              return (
                <tr
                  key={doc.id}
                  className={`transition-colors ${
                    isSelected ? "bg-accent-soft/40 font-semibold" : ""
                  }`}
                >
                  <td className="py-2.5 px-3">
                    <button type="button" onClick={() => onSelectDoc?.(doc.id)} aria-pressed={isSelected} className="min-h-11 text-left font-medium text-ink underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-accent">{doc.label_bn}</button>
                    <span className="text-[11px] text-muted">{doc.original_filename}</span>
                  </td>
                  <td className="py-2.5 px-3 text-ink max-w-[200px] truncate" title={owners}>
                    {owners}
                  </td>
                  <td className="py-2.5 px-3 font-mono text-ink">{dag}</td>
                  <td className="py-2.5 px-3 font-mono text-ink">{khatian}</td>
                  <td className="py-2.5 px-3 font-mono text-ink">{area}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
