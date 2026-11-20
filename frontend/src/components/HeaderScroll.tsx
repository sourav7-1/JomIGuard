"use client";

import { useEffect } from "react";

/** Marks <header data-scrolled> once the page scrolls, so the glass header gains a shadow. */
export function HeaderScroll() {
  useEffect(() => {
    const header = document.querySelector<HTMLElement>("header[data-glass]");
    if (!header) return;
    const update = () => { header.dataset.scrolled = String(window.scrollY > 4); };
    update();
    window.addEventListener("scroll", update, { passive: true });
    return () => window.removeEventListener("scroll", update);
  }, []);
  return null;
}
