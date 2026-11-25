"use client";

import { useEffect } from "react";

/** Marks <header data-scrolled> once the page scrolls, so the glass header gains a shadow,
 *  and publishes the header height as --header-h. */
export function HeaderScroll() {
  useEffect(() => {
    const header = document.querySelector<HTMLElement>("header[data-glass]");
    if (!header) return;
    const update = () => { header.dataset.scrolled = String(window.scrollY > 4); };
    update();
    window.addEventListener("scroll", update, { passive: true });
    // --header-h lets sticky page bars (the case journey stepper) sit right under the header
    const size = new ResizeObserver(() => document.documentElement.style.setProperty("--header-h", `${header.offsetHeight}px`));
    size.observe(header);
    return () => { window.removeEventListener("scroll", update); size.disconnect(); };
  }, []);
  return null;
}
