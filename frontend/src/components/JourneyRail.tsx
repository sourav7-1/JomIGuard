"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useLang } from "@/lib/lang";
import { api } from "@/lib/api";
import { Modal } from "@/components/ui/Modal";
import { forgetSession, useSession } from "@/lib/session";
import { ACCOUNT_LINKS, APP_NAV, HELP_LINKS, PUBLIC_NAV, activeNav, type NavKey, type NavLink } from "@/lib/nav";

const ICONS: Record<NavKey, string> = {
  home: "m3 11 9-8 9 8 M5.5 10v10h13V10 M9.5 20v-6h5v6",
  how: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Z M12 8v5 M12 16.5v.01",
  demo: "M4 7h16v12H4z M8 7V4h8v3 M9 12h6 M9 15.5h4",
  docs: "M6 3.75h8l4 4v12.5H6z M14 3.75v4h4 M9 12h6 M9 15.5h6",
  cases: "M4 4h7v7H4z M13 4h7v4h-7z M13 10h7v10h-7z M4 13h7v7H4z",
  new: "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14Z M20 20l-4-4 M11 8v6 M8 11h6",
  help: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6v.6 M12 17h.01",
  account: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM4 21a8 8 0 0 1 16 0",
};

function NavIcon({ k }: { k: NavKey }) {
  return <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" className="h-[19px] w-[19px] shrink-0"><path d={ICONS[k]} stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}

const desk = (active: boolean) =>
  `hidden min-h-12 items-center gap-2 border-b-2 px-3 text-sm font-medium transition-colors md:flex focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-accent ${active ? "border-gold text-accent" : "border-transparent text-muted hover:text-ink"}`;
const dock = (active: boolean) =>
  `flex min-h-14 min-w-0 flex-1 flex-col items-center justify-center gap-1 rounded-lg px-1 text-[11px] font-medium md:hidden ${active ? "bg-accent-soft text-accent" : "text-muted hover:text-ink"}`;

/** Help ▾ on desktop: native <details>, closed on route change and outside click. */
function HelpMenu({ active, en }: { active: boolean; en: boolean }) {
  const ref = useRef<HTMLDetailsElement>(null);
  const pathname = usePathname();
  useEffect(() => { if (ref.current) ref.current.open = false; }, [pathname]);
  useEffect(() => {
    const close = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) ref.current.open = false; };
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, []);
  return (
    <details ref={ref} className="relative hidden md:block">
      <summary className={`${desk(active)} cursor-pointer list-none [&::-webkit-details-marker]:hidden`} aria-current={active ? "page" : undefined}>
        <NavIcon k="help" />{en ? "Help" : "সাহায্য"}<span aria-hidden="true" className="text-xs">▾</span>
      </summary>
      <ul className="absolute left-0 top-full z-50 mt-1 min-w-52 rounded-[var(--radius-control)] border border-edge bg-surface p-1 shadow-overlay">
        {HELP_LINKS.map((l) => (
          <li key={l.href}><Link href={l.href} className="flex min-h-11 items-center gap-2 rounded-md px-3 text-sm text-ink hover:bg-bg"><NavIcon k={l.key} />{en ? l.en : l.bn}</Link></li>
        ))}
      </ul>
    </details>
  );
}

function SheetLinks({ links, en, onPick }: { links: NavLink[]; en: boolean; onPick: () => void }) {
  return (
    <ul className="space-y-1">
      {links.map((l) => (
        <li key={l.href}><Link href={l.href} onClick={onPick} className="flex min-h-12 items-center gap-3 rounded-[var(--radius-control)] border border-edge bg-bg/60 px-3 text-sm font-medium text-ink"><NavIcon k={l.key} />{en ? l.en : l.bn}</Link></li>
      ))}
    </ul>
  );
}

export function JourneyRail() {
  const pathname = usePathname();
  const router = useRouter();
  const en = useLang() === "en";
  const user = useSession();
  const signedIn = !!user;
  const active = activeNav(pathname, signedIn);
  const [sheet, setSheet] = useState<"help" | "account" | null>(null);
  if (user === undefined) return <div className="h-14 md:h-12" />;

  const label = en ? "Main navigation" : "প্রধান নেভিগেশন";
  const links = signedIn ? APP_NAV : PUBLIC_NAV;
  const logout = async () => {
    await api.logout().catch(() => undefined);
    forgetSession();
    setSheet(null);
    router.replace("/");
  };

  return (
    <nav aria-label={label} className="mobile-dock md:static md:mx-auto md:max-w-7xl md:px-8 md:pb-0">
      <div className="flex items-stretch justify-around border-t border-line bg-surface/95 px-1 pt-1 backdrop-blur-md md:justify-start md:gap-2 md:border-0 md:border-t md:bg-transparent md:p-0">
        {links.map((l) => (
          <Link key={l.href} href={l.href} aria-current={active === l.key ? "page" : undefined} className={desk(active === l.key)}>
            <NavIcon k={l.key} />{en ? l.en : l.bn}
          </Link>
        ))}
        {signedIn && <HelpMenu active={active === "help"} en={en} />}
        {links.map((l) => (
          <Link key={`m-${l.href}`} href={l.href} aria-current={active === l.key ? "page" : undefined} className={dock(active === l.key)}>
            <NavIcon k={l.key} /><span className="truncate">{en ? l.en : l.bn}</span>
          </Link>
        ))}
        {signedIn && <>
          <button type="button" aria-haspopup="dialog" onClick={() => setSheet("help")} className={dock(active === "help")}><NavIcon k="help" /><span className="truncate">{en ? "Help" : "সাহায্য"}</span></button>
          <button type="button" aria-haspopup="dialog" onClick={() => setSheet("account")} className={dock(active === "account")}><NavIcon k="account" /><span className="truncate">{en ? "Account" : "অ্যাকাউন্ট"}</span></button>
        </>}
      </div>
      <Modal open={sheet === "help"} onClose={() => setSheet(null)} title={en ? "Help" : "সাহায্য"}>
        <SheetLinks links={HELP_LINKS} en={en} onPick={() => setSheet(null)} />
      </Modal>
      <Modal open={sheet === "account"} onClose={() => setSheet(null)} title={user?.username ?? (en ? "Account" : "অ্যাকাউন্ট")}>
        <SheetLinks links={ACCOUNT_LINKS} en={en} onPick={() => setSheet(null)} />
        <button type="button" onClick={() => void logout()} className="mt-3 flex min-h-12 w-full items-center justify-center rounded-[var(--radius-control)] border border-line bg-surface text-sm font-semibold text-ink">{en ? "Log out" : "বের হন"}</button>
      </Modal>
    </nav>
  );
}
