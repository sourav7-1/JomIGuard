"use client";

import React, { createContext, useCallback, useContext, useState } from "react";
import { useLang } from "@/lib/lang";

type Tone = "ok" | "info" | "bad";
type Toast = { id: number; tone: Tone; text: string };

const ToastContext = createContext<(tone: Tone, text: string) => void>(() => {});

/** toast("ok" | "info" | "bad", text). Errors are announced assertively, others politely. */
export const useToast = () => useContext(ToastContext);

const style: Record<Tone, string> = {
  ok: "border-ok/40 text-ok",
  info: "border-sat/40 text-sat",
  bad: "border-bad/40 text-bad",
};
const icon: Record<Tone, string> = { ok: "✓", info: "i", bad: "!" };

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const en = useLang() === "en";
  const [toasts, setToasts] = useState<Toast[]>([]);
  const dismiss = (id: number) => setToasts((t) => t.filter((x) => x.id !== id));
  const push = useCallback((tone: Tone, text: string) => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t.slice(-2), { id, tone, text }]);
    window.setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), tone === "bad" ? 8000 : 5000);
  }, []);

  const list = (tones: Tone[]) => toasts.filter((t) => tones.includes(t.tone)).map((t) => (
    <div key={t.id} className={`pointer-events-auto flex items-start gap-3 rounded-[var(--radius-control)] border bg-[var(--glass)] p-3 pr-2 shadow-overlay backdrop-blur-md [animation:toast-in_250ms_var(--ease)_both] ${style[t.tone]}`}>
      <span aria-hidden="true" className="mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-current/15 text-xs font-bold">{icon[t.tone]}</span>
      <p className="min-w-0 flex-1 text-sm leading-6 text-ink">{t.text}</p>
      <button type="button" onClick={() => dismiss(t.id)} aria-label={en ? "Close message" : "বার্তা বন্ধ করুন"} className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-muted hover:bg-bg">×</button>
    </div>
  ));

  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="pointer-events-none fixed inset-x-3 bottom-24 z-[60] mx-auto flex max-w-sm flex-col gap-2 md:bottom-6 md:right-6 md:mx-0 md:ml-auto">
        <div aria-live="polite" role="status" className="flex flex-col gap-2">{list(["ok", "info"])}</div>
        <div aria-live="assertive" role="alert" className="flex flex-col gap-2">{list(["bad"])}</div>
      </div>
    </ToastContext.Provider>
  );
}
