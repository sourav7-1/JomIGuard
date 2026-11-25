// Navigation: which items exist (signed in or out) and which one is active on a route.

export type NavKey = "home" | "how" | "demo" | "docs" | "cases" | "new" | "help" | "account";
export type NavLink = { key: NavKey; href: string; bn: string; en: string };

export const PUBLIC_NAV: NavLink[] = [
  { key: "home", href: "/", bn: "হোম", en: "Home" },
  { key: "how", href: "/how-it-works", bn: "কীভাবে কাজ করে", en: "How it works" },
  { key: "demo", href: "/demo", bn: "নমুনা ডেটা", en: "Demo data" },
  { key: "docs", href: "/docs", bn: "ডকস", en: "Docs" },
];

export const APP_NAV: NavLink[] = [
  { key: "cases", href: "/dashboard", bn: "আমার কেস", en: "My cases" },
  { key: "new", href: "/find", bn: "নতুন যাচাই", en: "New check" },
];

export const HELP_LINKS: NavLink[] = [
  { key: "how", href: "/how-it-works", bn: "কীভাবে কাজ করে", en: "How it works" },
  { key: "help", href: "/help", bn: "প্রশ্নোত্তর", en: "Questions" },
  { key: "docs", href: "/docs", bn: "ডকস", en: "Docs" },
  { key: "demo", href: "/demo", bn: "নমুনা ডেটা", en: "Demo data" },
];

export const ACCOUNT_LINKS: NavLink[] = [
  { key: "account", href: "/profile", bn: "ক্রেতার পরিচয় যাচাই", en: "Buyer identity check" },
  { key: "home", href: "/?public=1", bn: "পাবলিক হোম", en: "Public home" },
];

const starts = (p: string, ...prefixes: string[]) => prefixes.some((x) => p === x || p.startsWith(`${x}/`));

/** The nav item to highlight. Signed in, info pages collapse into "help". */
export function activeNav(pathname: string, signedIn: boolean): NavKey | null {
  const p = pathname.replace(/\/+$/, "") || "/";
  if (starts(p, "/dashboard", "/cases", "/escrow", "/guardian")) return "cases";
  if (starts(p, "/find", "/upload")) return "new";
  if (starts(p, "/profile")) return "account";
  const info: [string, NavKey][] = [["/how-it-works", "how"], ["/demo", "demo"], ["/docs", "docs"], ["/help", "help"]];
  const hit = info.find(([prefix]) => starts(p, prefix));
  if (hit) return signedIn ? "help" : hit[1];
  if (p === "/") return signedIn ? null : "home";
  return null;
}
