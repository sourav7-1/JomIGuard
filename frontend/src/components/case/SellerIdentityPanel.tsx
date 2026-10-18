"use client";

import { useState } from "react";
import { api, IdentityVerificationOut } from "@/lib/api";
import { strings } from "@/lib/strings";

export function SellerIdentityPanel({
  landId, sellers, verifications,
}: {
  landId: string;
  sellers: { name: string }[];
  verifications: IdentityVerificationOut[];
}) {
  const [links, setLinks] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState("");
  if (!sellers.length) return null;

  const create = async (name: string) => {
    setBusy(name); setMessage("");
    try {
      const result = await api.createSellerLink(landId, name);
      setLinks((old) => ({ ...old, [name]: `${window.location.origin}${result.url}` }));
      setMessage(strings.identity.linkCreated);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : strings.identity.error);
    } finally { setBusy(""); }
  };

  const share = async (url: string) => {
    if (navigator.share) await navigator.share({ title: strings.identity.sellerHeading, url });
    else { await navigator.clipboard.writeText(url); setMessage(strings.identity.copy); }
  };

  return <section className="space-y-3 rounded-xl border border-line bg-surface p-4">
    <h2 className="font-heading text-lg font-bold">{strings.identity.sellerHeading}</h2>
    {sellers.map(({ name }) => {
      const result = [...verifications].reverse().find((v) => v.party === "seller" && v.seller_name_on_deed === name);
      const label = result?.status === "verified" ? strings.identity.verified
        : result?.status === "pending" ? strings.identity.pending
          : result?.status === "failed" ? strings.identity.failed : strings.identity.unverified;
      const url = links[name];
      return <div key={name} className="space-y-2 rounded-lg border border-line p-3">
        <div className="flex flex-wrap items-center justify-between gap-2"><span className="font-semibold">{name}</span><span className="rounded-full bg-bg px-2 py-1 text-xs">{label}</span></div>
        {url ? <div className="space-y-2"><p className="break-all text-xs text-muted">{url}</p><div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => navigator.clipboard.writeText(url).then(() => setMessage(strings.identity.copy))} className="min-h-11 rounded-lg border border-line px-3 text-sm">{strings.identity.copy}</button>
          <button type="button" onClick={() => share(url).catch(() => undefined)} className="min-h-11 rounded-lg border border-line px-3 text-sm">{strings.identity.share}</button>
        </div></div> : <button type="button" disabled={busy === name} onClick={() => create(name)} className="min-h-11 rounded-lg bg-accent px-3 text-sm font-semibold text-white disabled:opacity-60">{busy === name ? strings.labels.loading : strings.identity.createLink}</button>}
      </div>;
    })}
    {message && <p role="status" className="break-words text-sm text-muted">{message}</p>}
  </section>;
}
