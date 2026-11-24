"use client";

// Bangla / English switch. Kept in localStorage like the theme (a cookie read on the server
// would stop cacheComponents from prerendering every route). Server HTML is Bangla; the
// client swaps to English after hydration when the viewer picked it.
import { useEffect, useSyncExternalStore } from "react";

export type Lang = "bn" | "en";
const KEY = "jomiguard-lang";
const EVENT = "jomiguard:lang";

function subscribe(cb: () => void) {
  window.addEventListener(EVENT, cb);
  window.addEventListener("storage", cb);
  return () => {
    window.removeEventListener(EVENT, cb);
    window.removeEventListener("storage", cb);
  };
}

function getSnapshot(): Lang {
  try {
    return localStorage.getItem(KEY) === "en" ? "en" : "bn";
  } catch {
    return "bn";
  }
}

export function setLang(lang: Lang) {
  try {
    localStorage.setItem(KEY, lang);
  } catch {}
  document.documentElement.lang = lang;
  window.dispatchEvent(new Event(EVENT));
}

export function useLang(): Lang {
  return useSyncExternalStore(subscribe, getSnapshot, () => "bn");
}

/** `const t = useT(); t("বাংলা", "English")` inside client components. */
export function useT() {
  const lang = useLang();
  return (bn: string, en: string) => (lang === "en" ? en : bn);
}

/** Inline bilingual text, usable from server components too: <T bn="…" en="…" />. */
export function T({ bn, en }: { bn: React.ReactNode; en: React.ReactNode }) {
  return <>{useLang() === "en" ? en : bn}</>;
}

export function LangToggle() {
  const lang = useLang();
  const next: Lang = lang === "en" ? "bn" : "en";
  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);
  return (
    <button
      type="button"
      onClick={() => setLang(next)}
      aria-label={lang === "en" ? "বাংলায় দেখুন" : "Switch to English"}
      className="min-h-11 min-w-11 rounded-md border border-line bg-surface px-2.5 text-sm font-semibold text-ink transition-colors hover:bg-bg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
    >
      {lang === "en" ? "বাং" : "EN"}
    </button>
  );
}
