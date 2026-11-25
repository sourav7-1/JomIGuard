"use client";

import React, { useCallback, useEffect, useId, useRef, useState } from "react";
import { useLang } from "@/lib/lang";

// Native <dialog>: showModal() makes the rest of the page inert (focus trap), Esc fires
// "cancel", the browser returns focus to the trigger on close. Scroll lock and the
// desktop modal / mobile bottom-sheet look live in globals.css (dialog.modal).

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: React.ReactNode;
  description?: React.ReactNode;
  children?: React.ReactNode;
  footer?: React.ReactNode;
  wide?: boolean;
}

export function Modal({ open, onClose, title, description, children, footer, wide = false }: ModalProps) {
  const en = useLang() === "en";
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const descId = useId();

  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      className={`modal ${wide ? "modal-wide" : ""}`}
      aria-labelledby={titleId}
      aria-describedby={description ? descId : undefined}
      onCancel={(e) => { e.preventDefault(); onClose(); }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      {open && (
        <div className="modal-panel flex max-h-[inherit] flex-col overflow-hidden rounded-[var(--radius-card)] border border-edge bg-surface text-ink shadow-overlay">
          <div aria-hidden="true" className="mx-auto mt-2.5 h-1.5 w-10 shrink-0 rounded-full bg-line sm:hidden" />
          <header className="flex items-start justify-between gap-3 border-b border-line px-5 pb-3 pt-3 sm:pt-5">
            <div className="min-w-0 space-y-1">
              <h2 id={titleId} className="font-heading text-xl font-bold leading-snug text-ink">{title}</h2>
              {description && <p id={descId} className="text-sm leading-6 text-muted">{description}</p>}
            </div>
            <button type="button" onClick={onClose} aria-label={en ? "Close" : "বন্ধ করুন"} className="-mr-2 inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-xl text-muted transition-colors hover:bg-bg hover:text-ink">
              <span aria-hidden="true">×</span>
            </button>
          </header>
          <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 py-4">{children}</div>
          {footer && <footer className="flex flex-wrap justify-end gap-2 border-t border-line bg-bg/60 px-5 py-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">{footer}</footer>}
        </div>
      )}
    </dialog>
  );
}

type ConfirmOptions = { title: string; message: React.ReactNode; confirmLabel: string; danger?: boolean };

/** Promise-based confirm built on Modal (no browser confirm()). Render `dialog` once. */
export function useConfirm() {
  const en = useLang() === "en";
  const [state, setState] = useState<(ConfirmOptions & { resolve: (ok: boolean) => void }) | null>(null);
  const ask = useCallback((opts: ConfirmOptions) => new Promise<boolean>((resolve) => setState({ ...opts, resolve })), []);
  const done = (ok: boolean) => { state?.resolve(ok); setState(null); };
  const dialog = (
    <Modal
      open={!!state}
      onClose={() => done(false)}
      title={state?.title ?? ""}
      footer={<>
        <button type="button" onClick={() => done(false)} className="min-h-11 rounded-[var(--radius-control)] border border-line bg-surface px-4 text-sm font-semibold text-ink hover:bg-bg">{en ? "Go back" : "ফিরে যান"}</button>
        <button type="button" onClick={() => done(true)} className={`min-h-11 rounded-[var(--radius-control)] px-4 text-sm font-semibold text-white shadow-rest ${state?.danger ? "bg-bad" : "bg-accent"}`}>{state?.confirmLabel}</button>
      </>}
    >
      <div className="text-sm leading-7 text-ink">{state?.message}</div>
    </Modal>
  );
  return { ask, dialog };
}
