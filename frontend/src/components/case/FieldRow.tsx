"use client";

import React, { useState, useEffect } from "react";
import { ConfidenceBadge } from "./ConfidenceBadge";
import { strings } from "@/lib/strings";
import { EnumOption } from "@/lib/api";

interface FieldRowProps {
  path: string;
  labelBn: string;
  value: unknown;
  derivedValue?: unknown;
  flags?: string[] | string;
  editable: boolean;
  enumOptions?: EnumOption[] | null;
  isConfirmed: boolean;
  isEdited: boolean;
  errorMessage?: string | null;
  onConfirm: (path: string) => void;
  onEdit: (path: string, newValue: unknown) => void;
}

export function FieldRow({
  path,
  labelBn,
  value,
  derivedValue,
  flags,
  editable,
  enumOptions,
  isConfirmed,
  isEdited,
  errorMessage,
  onConfirm,
  onEdit,
}: FieldRowProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState<string>("");

  const handleStartEdit = () => {
    setEditValue(value !== undefined && value !== null ? String(value) : "");
    setIsEditing(true);
  };

  const handleSave = () => {
    setIsEditing(false);
    onEdit(path, editValue);
  };

  const handleCancel = () => {
    setIsEditing(false);
    setEditValue(value !== undefined && value !== null ? String(value) : "");
  };

  const displayVal =
    value !== undefined && value !== null && String(value).trim() !== ""
      ? String(value)
      : strings.casePage.emptyValue;

  const flagList = Array.isArray(flags)
    ? flags
    : typeof flags === "string"
      ? [flags]
      : [];

  const effectiveFlags = isConfirmed || isEdited ? ["human"] : flagList;

  const isLow = !isConfirmed && !isEdited && effectiveFlags.some((f) => f.toLowerCase() === "low");
  const isMedium = !isConfirmed && !isEdited && effectiveFlags.some((f) => f.toLowerCase() === "medium");

  const rowTint = isLow
    ? "bg-bad-bg/25 border-bad/30"
    : isMedium
      ? "bg-warn-bg/25 border-warn/30"
      : "bg-surface border-line/60";

  return (
    <div
      className={`p-2.5 rounded-lg border transition-colors ${rowTint} space-y-1`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="space-y-0.5 flex-1 min-w-0">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-xs font-semibold text-muted font-heading">
              {labelBn}
            </span>
            <ConfidenceBadge flags={effectiveFlags} />
            {isEdited && (
              <span className="text-[10px] font-medium bg-accent-soft text-accent px-1.5 py-0.2 rounded">
                সংশোধিত
              </span>
            )}
          </div>

          {!isEditing ? (
            <div className="flex flex-col sm:flex-row sm:items-baseline gap-1 sm:gap-3">
              <span className="text-sm font-medium font-mono text-ink break-words">
                {displayVal}
              </span>
              {derivedValue !== undefined && derivedValue !== null && String(derivedValue).trim() !== "" && (
                <span className="text-xs text-muted font-mono bg-bg/60 px-1.5 py-0.5 rounded border border-line/50 self-start">
                  হিসাবকৃত: {String(derivedValue)}
                </span>
              )}
            </div>
          ) : (
            <div className="pt-1 space-y-2">
              {enumOptions && enumOptions.length > 0 ? (
                <select
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                  className="w-full text-sm p-1.5 rounded border border-line bg-surface text-ink focus:outline-accent"
                >
                  <option value="">নির্বাচন করুন</option>
                  {enumOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label_bn} ({opt.value})
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                  aria-label={labelBn}
                  placeholder={labelBn}
                  className="w-full text-sm p-1.5 rounded border border-line bg-surface text-ink font-mono focus:outline-accent"
                />
              )}
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={handleSave}
                  className="px-2.5 py-1 text-xs font-medium rounded bg-accent text-surface hover:opacity-90 min-h-[36px]"
                >
                  {strings.casePage.saveField}
                </button>
                <button
                  type="button"
                  onClick={handleCancel}
                  className="px-2.5 py-1 text-xs font-medium rounded border border-line bg-surface text-muted hover:bg-bg min-h-[36px]"
                >
                  {strings.casePage.cancelEdit}
                </button>
              </div>
            </div>
          )}
        </div>

        {editable && !isEditing && (
          <div className="flex items-center gap-1 shrink-0">
            <button
              type="button"
              onClick={() => onConfirm(path)}
              disabled={isConfirmed}
              title={strings.casePage.confirmField}
              aria-label={`${labelBn} ${strings.casePage.confirmField}`}
              className={`text-xs px-2 py-1 rounded min-h-[36px] font-medium border transition-colors ${
                isConfirmed
                  ? "bg-ok-bg text-ok border-ok/30 opacity-75"
                  : "bg-surface hover:bg-bg text-ink border-line"
              }`}
            >
              {isConfirmed ? "✓ নিশ্চিত" : strings.casePage.confirmField}
            </button>
            <button
              type="button"
              onClick={handleStartEdit}
              title={strings.casePage.editField}
              aria-label={`${labelBn} ${strings.casePage.editField}`}
              className="text-xs px-2 py-1 rounded min-h-[36px] font-medium border border-line bg-surface hover:bg-bg text-accent"
            >
              {strings.casePage.editField}
            </button>
          </div>
        )}
      </div>

      {errorMessage && (
        <div className="text-xs text-bad font-medium pt-0.5">
          {errorMessage}
        </div>
      )}
    </div>
  );
}
