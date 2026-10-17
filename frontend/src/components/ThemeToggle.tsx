"use client";

import React, { useSyncExternalStore } from "react";
import { strings } from "@/lib/strings";

function subscribe(callback: () => void) {
  window.addEventListener("storage", callback);
  return () => window.removeEventListener("storage", callback);
}

function getSnapshot(): "light" | "dark" {
  if (typeof window === "undefined") return "light";
  const saved = localStorage.getItem("jomiguard-theme");
  if (saved === "light" || saved === "dark") return saved;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function getServerSnapshot(): "light" | "dark" {
  return "light";
}

export function ThemeToggle() {
  const theme = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const toggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    localStorage.setItem("jomiguard-theme", next);
    document.documentElement.setAttribute("data-theme", next);
    window.dispatchEvent(new Event("storage"));
  };

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={strings.buttons.themeToggle}
      className="min-h-[44px] min-w-[44px] px-3 py-2 rounded-lg border border-line bg-surface text-ink hover:bg-bg transition-colors flex items-center justify-center gap-1.5 text-xs font-medium cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
    >
      <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" className="h-4 w-4">
        {theme === "dark" ? (
          <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="1.7" />
        ) : (
          <path d="M20 15.2A8 8 0 0 1 8.8 4 8 8 0 1 0 20 15.2Z" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
        )}
      </svg>
      <span>
        {theme === "dark" ? strings.labels.lightTheme : strings.labels.darkTheme}
      </span>
    </button>
  );
}
