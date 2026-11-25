"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useT } from "@/lib/lang";
import { forgetSession, useSession } from "@/lib/session";
import { ACCOUNT_LINKS } from "@/lib/nav";

const solid = "inline-flex min-h-11 items-center rounded-[var(--radius-control)] bg-gradient-to-b from-accent to-[#23317A] px-4 text-sm font-semibold text-white shadow-rest hover:shadow-raised";

/** Signed out: the login button. Signed in (desktop): the account menu; phones use the dock. */
export function AuthControls() {
  const router = useRouter();
  const pathname = usePathname();
  const t = useT();
  const user = useSession();
  const ref = useRef<HTMLDetailsElement>(null);
  useEffect(() => { if (ref.current) ref.current.open = false; }, [pathname]);

  if (user === undefined || pathname === "/login") return null;
  if (!user) return <Link href="/login" className={solid}>{t("প্রবেশ করুন", "Log in")}</Link>;
  const logout = async () => {
    await api.logout().catch(() => undefined);
    forgetSession();
    router.replace("/");
  };
  return (
    <details ref={ref} className="relative hidden md:block">
      <summary className="inline-flex min-h-11 cursor-pointer list-none items-center gap-2 rounded-md border border-line bg-surface px-3 text-sm font-semibold text-ink hover:bg-bg [&::-webkit-details-marker]:hidden">
        <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" className="h-4 w-4"><path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM4 21a8 8 0 0 1 16 0" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg>
        {user.username}<span aria-hidden="true" className="text-xs">▾</span>
      </summary>
      <ul className="absolute right-0 top-full z-50 mt-1 min-w-56 rounded-[var(--radius-control)] border border-edge bg-surface p-1 shadow-overlay">
        {ACCOUNT_LINKS.map((l) => (
          <li key={l.href}><Link href={l.href} className="flex min-h-11 items-center rounded-md px-3 text-sm text-ink hover:bg-bg">{t(l.bn, l.en)}</Link></li>
        ))}
        <li><button type="button" onClick={() => void logout()} className="flex min-h-11 w-full items-center rounded-md px-3 text-left text-sm text-ink hover:bg-bg">{t("বের হন", "Log out")}</button></li>
      </ul>
    </details>
  );
}
