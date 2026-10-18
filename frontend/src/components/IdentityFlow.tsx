"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import { api, IdentityVerificationOut } from "@/lib/api";
import { strings } from "@/lib/strings";

type Outcome = "verified" | "failed" | "pending";

function CameraStep({ title, onContinue }: { title: string; onContinue: () => void }) {
  const video = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const previewRef = useRef("");
  const [preview, setPreview] = useState("");
  const [cameraError, setCameraError] = useState(false);
  const [cameraOn, setCameraOn] = useState(false);

  useEffect(() => {
    return () => {
      stream.current?.getTracks().forEach((track) => track.stop());
      stream.current = null;
      if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    };
  }, []);

  const startCamera = () => {
    navigator.mediaDevices?.getUserMedia({ video: { facingMode: "user" }, audio: false })
      .then((media) => { stream.current = media; setCameraOn(true); if (video.current) video.current.srcObject = media; })
      .catch(() => setCameraError(true));
  };

  const capture = () => {
    const node = video.current;
    if (!node || !node.videoWidth) return;
    const canvas = document.createElement("canvas");
    canvas.width = node.videoWidth; canvas.height = node.videoHeight;
    canvas.getContext("2d")?.drawImage(node, 0, 0);
    canvas.toBlob((blob) => {
      if (blob) {
        const url = URL.createObjectURL(blob);
        previewRef.current = url;
        setPreview(url);
      }
    }, "image/jpeg", 0.8);
  };

  const next = () => { if (previewRef.current) URL.revokeObjectURL(previewRef.current); previewRef.current = ""; setPreview(""); onContinue(); };

  return <section className="space-y-4">
    <h2 className="font-heading text-xl font-bold">{title}</h2>
    <p className="rounded-lg border border-warn/40 bg-warn-bg p-3 text-sm">{strings.identity.demoNote}</p>
    <p className="text-sm text-muted">{strings.identity.cameraHint}</p>
    {preview ? <Image src={preview} alt={title} width={640} height={480} unoptimized className="mx-auto max-h-72 rounded-xl object-contain" />
      : <video ref={video} autoPlay playsInline muted className="mx-auto aspect-video w-full max-w-lg rounded-xl bg-black object-cover" />}
    {cameraError && <p role="status" className="text-sm text-muted">{strings.identity.noCamera}</p>}
    <div className="flex flex-wrap gap-2">
      {!preview && !cameraError && !cameraOn && <button type="button" onClick={startCamera} className="min-h-11 rounded-lg border border-line px-4">{strings.identity.cameraStart}</button>}
      {!preview && !cameraError && cameraOn && <button type="button" onClick={capture} className="min-h-11 rounded-lg border border-line px-4">{strings.identity.capture}</button>}
      <button type="button" onClick={next} className="min-h-11 rounded-lg bg-accent px-4 font-semibold text-white">{strings.identity.continue}</button>
    </div>
  </section>;
}

export function IdentityFlow({ mode, token }: { mode: "seller" | "buyer"; token?: string }) {
  const [step, setStep] = useState(0);
  const [land, setLand] = useState<{ mouza: string; dag_no: string; message_bn: string; escrow_agreement_requested: boolean } | null>(null);
  const [sellerAgreed, setSellerAgreed] = useState(false);
  const [name, setName] = useState("");
  const [fatherName, setFatherName] = useState("");
  const [outcome, setOutcome] = useState<Outcome>("verified");
  const [result, setResult] = useState<IdentityVerificationOut | null>(null);
  const [savedBuyerResults, setSavedBuyerResults] = useState<IdentityVerificationOut[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const title = mode === "seller" ? strings.identity.sellerHeading : strings.identity.buyerTitle;

  useEffect(() => {
    if (mode === "buyer") {
      api.getBuyerVerifications().then(setSavedBuyerResults).catch(() => undefined);
      return;
    }
    if (!token) return;
    api.getSellerLink(token).then(setLand).catch(() => setError(strings.identity.expired));
  }, [mode, token]);

  const consent = async () => {
    setBusy(true); setError("");
    try { if (mode === "seller" && token) await api.consentSeller(token); setStep(2); }
    catch (e) { setError(e instanceof Error ? e.message : strings.identity.error); }
    finally { setBusy(false); }
  };

  const submit = async () => {
    setBusy(true); setError("");
    try {
      const saved = mode === "seller" && token
        ? await api.completeSellerVerification(token, { name, father_name: fatherName, outcome })
        : await api.verifyBuyer({ name, father_name: fatherName, outcome, consent: true });
      setResult(saved); setStep(5);
      if (mode === "buyer") setSavedBuyerResults((old) => [saved, ...old]);
    } catch (e) { setError(e instanceof Error ? e.message : strings.identity.error); }
    finally { setBusy(false); }
  };

  const remove = async () => {
    if (!result) return;
    setBusy(true);
    try {
      if (mode === "seller" && token) await api.deleteSellerVerification(token);
      else await api.deleteBuyerVerification(result.id);
      if (mode === "buyer") setSavedBuyerResults((old) => old.filter((item) => item.id !== result.id));
      setResult(null); setStep(0); setName(""); setFatherName("");
      setError(strings.identity.deleted);
    } catch (e) { setError(e instanceof Error ? e.message : strings.identity.error); }
    finally { setBusy(false); }
  };

  const agreeEscrow = async () => {
    if (!token || !land?.escrow_agreement_requested) return;
    setBusy(true); setError("");
    try { await api.sellerAgreeEscrow(token); setSellerAgreed(true); }
    catch (e) { setError(e instanceof Error ? e.message : strings.identity.error); }
    finally { setBusy(false); }
  };

  return <main className="mx-auto max-w-2xl space-y-5 rounded-2xl border border-line bg-surface p-4 sm:p-7">
    <h1 className="font-heading text-2xl font-bold">{title}</h1>
    {mode === "seller" && land && <div className="rounded-xl border border-line bg-bg p-4"><p>{land.message_bn}</p><p className="mt-2 text-sm text-muted">{strings.casePage.mouza}: {land.mouza} · {strings.casePage.dag}: {land.dag_no}</p></div>}
    {mode === "seller" && !land && !error && <p className="text-sm text-muted">{strings.labels.loading}</p>}
    {mode === "buyer" && <p className="text-sm text-muted">{strings.identity.buyerPrompt}</p>}
    {mode === "buyer" && savedBuyerResults.map((item) => <section key={item.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-line p-3"><span>{item.name_bn_as_per_nid || strings.identity.pending} · {item.status === "verified" ? strings.identity.verified : item.status === "failed" ? strings.identity.failed : strings.identity.pending}</span><button type="button" onClick={() => api.deleteBuyerVerification(item.id).then(() => setSavedBuyerResults((old) => old.filter((saved) => saved.id !== item.id))).catch(() => setError(strings.identity.error))} className="min-h-11 rounded-lg border border-line px-3 text-sm">{strings.identity.delete}</button></section>)}
    {mode === "buyer" && step === 0 && <p className="text-sm text-muted">{strings.identity.noPhone}</p>}
    {step === 0 && mode === "seller" && land && <button type="button" onClick={() => setStep(1)} className="min-h-11 rounded-lg bg-accent px-4 font-semibold text-white">{strings.identity.continue}</button>}
    {step === 0 && mode === "buyer" && <button type="button" onClick={() => setStep(1)} className="min-h-11 rounded-lg bg-accent px-4 font-semibold text-white">{strings.identity.continue}</button>}
    {step === 1 && <section className="space-y-3"><h2 className="font-heading text-xl font-bold">{strings.identity.consentTitle}</h2>
      <ul className="list-disc space-y-2 pl-5 text-sm leading-relaxed"><li>{strings.identity.consentWhat}</li><li>{strings.identity.consentWho}</li><li>{mode === "seller" ? strings.identity.consentWhySeller : strings.identity.consentWhyBuyer}</li><li>{strings.identity.consentKeep}</li><li>{strings.identity.consentDelete}</li></ul>
      <button type="button" disabled={busy} onClick={consent} className="min-h-11 rounded-lg bg-accent px-4 font-semibold text-white disabled:opacity-60">{busy ? strings.labels.loading : strings.identity.agree}</button>
    </section>}
    {(step === 2 || step === 3) && <CameraStep title={step === 2 ? strings.identity.nidPhoto : strings.identity.selfie} onContinue={() => setStep(step + 1)} />}
    {step === 4 && <section className="space-y-4"><p className="rounded-lg border border-warn/40 bg-warn-bg p-3 text-sm">{strings.identity.demoNote}</p>
      <label className="block space-y-1 text-sm"><span>{strings.identity.name}</span><input required value={name} onChange={(e) => setName(e.target.value)} className="min-h-11 w-full rounded-lg border border-line bg-bg px-3" /></label>
      <label className="block space-y-1 text-sm"><span>{strings.identity.fatherName}</span><input required value={fatherName} onChange={(e) => setFatherName(e.target.value)} className="min-h-11 w-full rounded-lg border border-line bg-bg px-3" /></label>
      <label className="block space-y-1 text-sm"><span>{strings.identity.outcome}</span><select value={outcome} onChange={(e) => setOutcome(e.target.value as Outcome)} className="min-h-11 w-full rounded-lg border border-line bg-bg px-3"><option value="verified">{strings.identity.outcomeVerified}</option><option value="failed">{strings.identity.outcomeFailed}</option><option value="pending">{strings.identity.outcomePending}</option></select></label>
      <button type="button" disabled={busy || !name.trim() || !fatherName.trim()} onClick={submit} className="min-h-11 rounded-lg bg-accent px-4 font-semibold text-white disabled:opacity-60">{busy ? strings.labels.loading : strings.identity.submit}</button>
    </section>}
    {step === 5 && result && <section className="space-y-3 rounded-xl border border-line p-4"><h2 className="font-heading text-xl font-bold">{strings.identity.resultTitle}</h2><p>{result.status === "verified" ? strings.identity.verified : result.status === "failed" ? strings.identity.failed : strings.identity.pending}</p><p className="text-sm text-muted">{result.name_bn_as_per_nid || "—"}</p>{land?.escrow_agreement_requested && result.status === "verified" && <button type="button" disabled={busy || sellerAgreed} onClick={agreeEscrow} className="min-h-11 rounded-lg bg-accent px-4 text-sm font-semibold text-white">{sellerAgreed ? "বায়না চুক্তিতে সম্মতি দেওয়া হয়েছে" : "বায়না চুক্তিতে সম্মতি দিন"}</button>}<button type="button" disabled={busy} onClick={remove} className="min-h-11 rounded-lg border border-line px-4 text-sm">{busy ? strings.labels.loading : strings.identity.delete}</button></section>}
    {error && <p role="alert" className="rounded-lg border border-warn/40 bg-warn-bg p-3 text-sm">{error}</p>}
  </main>;
}
