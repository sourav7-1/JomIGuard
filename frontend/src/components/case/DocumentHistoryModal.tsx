"use client";

import React, { useState, useEffect } from "react";
import { api, ExtractionOut } from "@/lib/api";
import { Skeleton } from "@/components/ui/Skeleton";
import { Modal } from "@/components/ui/Modal";
import { useLang, useStrings } from "@/lib/lang";

interface DocumentHistoryModalProps {
  documentId: string;
  isOpen: boolean;
  onClose: () => void;
}

export function DocumentHistoryModal({
  documentId,
  isOpen,
  onClose,
}: DocumentHistoryModalProps) {
  const strings = useStrings();
  const en = useLang() === "en";
  const t = (b: string, e: string) => (en ? e : b);
  const [history, setHistory] = useState<ExtractionOut[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      // The modal needs an immediate loading state while its request is pending.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setLoading(true);
      api
        .getDocumentExtractionHistory(documentId)
        .then((res) => {
          setHistory(Array.isArray(res) ? res : [res]);
        })
        .catch(() => {
          setHistory([]);
        })
        .finally(() => setLoading(false));
    }
  }, [documentId, isOpen]);

  // The original AI extraction is the oldest one in history (last item when sorted desc)
  const aiExtraction = history.length > 0 ? history[history.length - 1] : null;

  return (
    <Modal
      open={isOpen}
      onClose={onClose}
      title={strings.casePage.historyTitle}
      footer={<button type="button" onClick={onClose} className="min-h-11 rounded-[var(--radius-control)] border border-line bg-surface px-4 text-sm font-medium text-ink hover:bg-bg">{strings.casePage.historyClose}</button>}
    >
      {loading ? (
        <div className="space-y-2" role="status" aria-label={strings.labels.loading}><Skeleton className="h-4 w-1/2" /><Skeleton className="h-40 w-full" /></div>
      ) : !aiExtraction ? (
        <p className="py-4 text-center text-sm text-muted">{strings.casePage.noHistory}</p>
      ) : (
        <div className="space-y-3 font-mono text-sm">
          <div className="flex items-center justify-between border-b border-line pb-2 text-xs text-muted">
            <span>{t("মডেল", "Model")}: {aiExtraction.extractor}</span>
            <span>{t("তারিখ", "Date")}: {new Date(aiExtraction.created_at).toLocaleString(en ? "en-GB" : "bn-BD")}</span>
          </div>
          <div className="overflow-x-auto whitespace-pre-wrap rounded-[var(--radius-control)] border border-line bg-bg/40 p-3 text-xs leading-relaxed">
            {JSON.stringify(aiExtraction.data, null, 2)}
          </div>
        </div>
      )}
    </Modal>
  );
}
