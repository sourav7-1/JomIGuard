"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { strings } from "@/lib/strings";
import { Spinner } from "@/components/ui/Spinner";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [authorizedPath, setAuthorizedPath] = useState("");

  useEffect(() => {
    if (pathname === "/login" || pathname === "/offline" || pathname.startsWith("/verify/")) return;
    let active = true;
    const redirectToLogin = () => router.replace(`/login?next=${encodeURIComponent(pathname)}&expired=1`);
    const redirectForMissingSession = () => router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    const redirectOffline = () => router.replace("/offline");
    window.addEventListener("jomiguard:unauthorized", redirectToLogin);
    window.addEventListener("jomiguard:offline", redirectOffline);
    api.getMe().then(() => {
      if (active) setAuthorizedPath(pathname);
    }).catch((error: unknown) => {
      if (error instanceof ApiError && error.status === 0) redirectOffline();
      else redirectForMissingSession();
    });
    return () => {
      active = false;
      window.removeEventListener("jomiguard:unauthorized", redirectToLogin);
      window.removeEventListener("jomiguard:offline", redirectOffline);
    };
  }, [pathname, router]);

  if (pathname === "/login" || pathname === "/offline" || pathname.startsWith("/verify/") || authorizedPath === pathname) return children;
  return <div className="flex min-h-[50vh] items-center justify-center gap-3 text-sm text-muted"><Spinner />{strings.auth.checking}</div>;
}
