"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { strings } from "@/lib/strings";

export function AuthControls() {
  const router = useRouter();
  const [signedIn, setSignedIn] = useState(false);
  useEffect(() => {
    api.getMe().then(() => setSignedIn(true)).catch(() => setSignedIn(false));
  }, []);
  if (!signedIn) return null;
  return <button type="button" onClick={async () => { await api.logout().catch(() => undefined); router.replace("/login"); }} className="min-h-11 rounded-md border border-line bg-surface px-3 text-sm font-semibold text-ink hover:bg-bg">{strings.auth.logout}</button>;
}
