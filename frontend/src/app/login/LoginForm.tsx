"use client";

import { type FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { strings } from "@/lib/strings";
import { useT } from "@/lib/lang";

const input = "min-h-12 w-full rounded-lg border border-line bg-bg px-3 font-normal outline-none focus:border-accent focus:ring-2 focus:ring-accent/20";

export function LoginForm({ nextPath, sessionExpired = false }: { nextPath: string; sessionExpired?: boolean }) {
  const router = useRouter();
  const t = useT();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError("");
    try {
      await api.login(String(form.get("username") || ""), String(form.get("password") || ""));
      router.replace(nextPath.startsWith("/") && !nextPath.startsWith("//") ? nextPath : "/dashboard");
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : t(strings.auth.failed, "Could not sign in. Please try again."));
    } finally {
      setBusy(false);
    }
  };
  return <form onSubmit={submit} className="mx-auto w-full max-w-md space-y-5 rounded-2xl border border-line bg-surface p-6 shadow-sm sm:p-8">
    <div>
      <h1 className="font-heading text-2xl font-bold text-ink">{t(strings.auth.title, "Sign in")}</h1>
      <p className="mt-2 text-sm leading-6 text-muted">{t(strings.auth.desc, "Sign in to see your cases and documents.")}</p>
    </div>
    {sessionExpired && <p role="status" className="rounded-lg border border-warn/40 bg-warn-bg p-3 text-sm text-ink">{t(strings.auth.sessionEnded, "Session ended — please sign in again")}</p>}
    <label className="block space-y-2 text-sm font-semibold text-ink">{t(strings.auth.username, "Username")}<input required name="username" autoComplete="username" className={input} /></label>
    <label className="block space-y-2 text-sm font-semibold text-ink">{t(strings.auth.password, "Password")}<input required name="password" type="password" autoComplete="current-password" className={input} /></label>
    {error && <p role="alert" className="rounded-lg border border-bad/30 bg-bad-bg p-3 text-sm text-bad">{error}{error === strings.error.offlineMessage && <Link className="ml-2 underline" href="/offline">{strings.error.offlineTitle}</Link>}</p>}
    <button disabled={busy} className="min-h-12 w-full rounded-lg bg-accent px-4 font-semibold text-white disabled:opacity-60">{busy ? t(strings.labels.loading, "Loading…") : t(strings.auth.submit, "Sign in")}</button>
    <p className="text-center text-sm text-muted"><Link href="/" className="font-semibold text-accent underline underline-offset-4">{t("← মূল পাতায় ফিরুন", "← Back to home")}</Link></p>
  </form>;
}
