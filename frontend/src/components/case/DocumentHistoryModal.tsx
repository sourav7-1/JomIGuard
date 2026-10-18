"use client";

import React, { useState, useEffect } from "react";
import { api, ExtractionOut } from "@/lib/api";
import { strings } from "@/lib/strings";
import { Spinner } from "@/components/ui/Spinner";

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

  if (!isOpen) return null;

  // The original AI extraction is the oldest one in history (last item when sorted desc)
  const aiExtraction = history.length > 0 ? history[history.length - 1] : null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/50 backdrop-blur-xs"
    >
      <div className="bg-surface border border-line rounded-xl shadow-xl max-w-lg w-full max-h-[85vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-line">
          <h3 className="font-heading font-bold text-ink text-base">
            {strings.casePage.historyTitle}
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="text-muted hover:text-ink text-lg font-bold w-8 h-8 flex items-center justify-center rounded"
          >
            ✕
          </button>
        </div>

        <div className="p-4 overflow-y-auto space-y-3 flex-1 text-sm font-mono">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Spinner size="md" />
            </div>
          ) : !aiExtraction ? (
            <div className="text-muted text-center py-4">
              {strings.casePage.noHistory}
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs text-muted pb-2 border-b border-line">
                <span>মডেল: {aiExtraction.extractor}</span>
                <span>
                  তারিখ: {new Date(aiExtraction.created_at).toLocaleString("bn-BD")}
                </span>
              </div>
              <div className="bg-bg/40 p-3 rounded-lg border border-line overflow-x-auto text-xs whitespace-pre-wrap leading-relaxed">
                {JSON.stringify(aiExtraction.data, null, 2)}
              </div>
            </div>
          )}
        </div>

        <div className="p-3 border-t border-line flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium rounded-lg border border-line bg-surface hover:bg-bg text-ink min-h-[44px]"
          >
            {strings.casePage.historyClose}
          </button>
        </div>
      </div>
    </div>
  );
}
