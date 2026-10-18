"use client";

import { strings } from "@/lib/strings";

export default function GlobalError({ retry }: { error: Error & { digest?: string }; retry: () => void }) {
  return (
    <html lang="bn"><body style={{ margin: 0, padding: 32, fontFamily: "sans-serif", textAlign: "center" }}>
      <h1>{strings.error.serverErrorTitle}</h1>
      <p>{strings.error.serverError}</p>
      <button type="button" onClick={retry} style={{ minHeight: 44, padding: "0 20px" }}>{strings.error.retryPage}</button>
    </body></html>
  );
}
