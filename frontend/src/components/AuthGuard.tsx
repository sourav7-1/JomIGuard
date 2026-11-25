"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { strings } from "@/lib/strings";
import { Spinner } from "@/components/ui/Spinner";
import { useSession } from "@/lib/session";

// Pages anyone can open without signing in.
const PUBLIC = ["/", "/login", "/offline", "/help", "/docs", "/how-it-works", "/demo"];
const isPublic = (p: string) => PUBLIC.includes(p) || p.startsWith("/verify/");

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [authorizedPath, setAuthorizedPath] = useState("");
  const user = useSession();

  // Signed-in users opening the public home land on their cases; "/?public=1" keeps the home.
  useEffect(() => {
    if (pathname === "/" && user && !new URLSearchParams(window.location.search).has("public")) router.replace("/dashboard");
  }, [pathname, user, router]);

  useEffect(() => {
    if (isPublic(pathname)) return;
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

  if (isPublic(pathname) || authorizedPath === pathname) return children;
  return <div className="flex min-h-[50vh] items-center justify-center gap-3 text-sm text-muted"><Spinner />{strings.auth.checking}</div>;
}
