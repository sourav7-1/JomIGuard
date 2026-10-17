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
      <span aria-hidden="true" className="text-sm">
        {theme === "dark" ? "☀️" : "🌙"}
      </span>
      <span>
        {theme === "dark" ? strings.labels.lightTheme : strings.labels.darkTheme}
      </span>
    </button>
  );
}
