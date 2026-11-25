"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { api } from "@/lib/api";

type Me = { id: string; username: string } | null;

// One /auth/me request per navigation, shared by the header, nav and guard.
let cached: { path: string; promise: Promise<Me> } | null = null;

function me(path: string): Promise<Me> {
  if (cached?.path !== path) cached = { path, promise: api.getMe().catch(() => null) };
  return cached.promise;
}

export function forgetSession() {
  cached = null;
}

/** undefined while checking, null when signed out. Re-checked on every route change. */
export function useSession(): Me | undefined {
  const pathname = usePathname();
  const [user, setUser] = useState<Me | undefined>(undefined);
  useEffect(() => {
    let live = true;
    me(pathname).then((u) => { if (live) setUser(u); });
    return () => { live = false; };
  }, [pathname]);
  return user;
}
