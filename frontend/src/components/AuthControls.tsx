"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useT } from "@/lib/lang";

const ghost = "inline-flex min-h-11 items-center rounded-md border border-line bg-surface px-3 text-sm font-semibold text-ink hover:bg-bg";
const solid = "inline-flex min-h-11 items-center rounded-[var(--radius-control)] bg-gradient-to-b from-accent to-[#23317A] px-4 text-sm font-semibold text-white shadow-rest hover:shadow-raised";

export function AuthControls() {
  const router = useRouter();
  const pathname = usePathname();
  const t = useT();
  const [signedIn, setSignedIn] = useState<boolean | null>(null);
  // Re-check on navigation so the header flips right after login/logout.
  useEffect(() => {
    api.getMe().then(() => setSignedIn(true)).catch(() => setSignedIn(false));
  }, [pathname]);

  if (signedIn === null || pathname === "/login") return null;
  if (!signedIn) return <Link href="/login" className={solid}>{t("প্রবেশ করুন", "Login")}</Link>;
  return <>
    {pathname !== "/dashboard" && <Link href="/dashboard" className={solid}>{t("ড্যাশবোর্ড", "Dashboard")}</Link>}
    <button type="button" onClick={async () => { await api.logout().catch(() => undefined); setSignedIn(false); router.replace("/"); }} className={ghost}>{t("বের হন", "Logout")}</button>
  </>;
}
