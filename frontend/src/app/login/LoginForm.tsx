"use client";

import { type FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { strings } from "@/lib/strings";

export function LoginForm({ nextPath, sessionExpired = false }: { nextPath: string; sessionExpired?: boolean }) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError("");
    try {
      await api.login(String(form.get("username") || ""), String(form.get("password") || ""));
      router.replace(nextPath.startsWith("/") && !nextPath.startsWith("//") ? nextPath : "/cases");
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : strings.auth.failed);
    } finally {
      setBusy(false);
    }
  };
  return <form onSubmit={submit} className="mx-auto w-full max-w-md space-y-5 rounded-2xl border border-line bg-surface p-6 shadow-sm sm:p-8">
    <div><h1 className="font-heading text-2xl font-bold text-ink">{strings.auth.title}</h1><p className="mt-2 text-sm leading-6 text-muted">{strings.auth.desc}</p></div>
    {sessionExpired && <p role="status" className="rounded-lg border border-warn/40 bg-warn-bg p-3 text-sm text-ink">{strings.auth.sessionEnded}</p>}
    <label className="block space-y-2 text-sm font-semibold text-ink">{strings.auth.username}<input required name="username" autoComplete="username" className="min-h-12 w-full rounded-lg border border-line bg-bg px-3 font-normal outline-none focus:border-accent focus:ring-2 focus:ring-accent/20" /></label>
    <label className="block space-y-2 text-sm font-semibold text-ink">{strings.auth.password}<input required name="password" type="password" autoComplete="current-password" className="min-h-12 w-full rounded-lg border border-line bg-bg px-3 font-normal outline-none focus:border-accent focus:ring-2 focus:ring-accent/20" /></label>
    {error && <p role="alert" className="rounded-lg border border-bad/30 bg-bad-bg p-3 text-sm text-bad">{error}{error === strings.error.offlineMessage && <Link className="ml-2 underline" href="/offline">{strings.error.offlineTitle}</Link>}</p>}
    <button disabled={busy} className="min-h-12 w-full rounded-lg bg-accent px-4 font-semibold text-white disabled:opacity-60">{busy ? strings.labels.loading : strings.auth.submit}</button>
  </form>;
}
