# JomiGuard demo runbook

Use only the generated cases in this repository. The full walkthrough takes about 6 minutes.

## Start the demo on Windows

1. Start Docker Desktop and wait until its engine is running.
2. Open the repository `.env` and set `COOKIE_SECURE=true`. This is needed because the public
   tunnel uses HTTPS. Do not paste `.env` values into chat or a presentation.
3. In Command Prompt:

   ```cmd
   cd /d C:\JomiGuard
   docker compose up -d --build
   docker compose ps
   docker compose exec backend python -m app.scripts.demo_reset
   ```

   Wait for frontend, backend, worker, Postgres, Redis, and MinIO to report running/healthy. `demo_reset`
   prepares the three synthetic cases, guardian samples, buyer verification, and a fresh draft
   escrow deal for case 00026 on every run. Older demo deals are archived; their event and bank
   ledger history remains stored. Use the Home page's case 00026 escrow link, which always opens
   the current unarchived deal at step 1.

4. The frontend builds and starts in Docker on port 3000. Check `docker compose ps` and open
   `http://localhost:3000`; sign in with the admin username and password from `.env`. Its `/api/*`
   requests are proxied inside Compose to `http://backend:8000`.

## Temporary public link

Install `cloudflared` if it is not already available. On Windows, run
`winget install --id Cloudflare.cloudflared` in PowerShell, open a new terminal, and check with
`cloudflared --version`. If winget is unavailable, download the Windows installer or binary from
[Cloudflare's Tunnel downloads](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/)
page and follow its Windows instructions.

With the frontend still running, open another terminal and run:

```cmd
cloudflared tunnel --url http://localhost:3000
```

Share the `https://…trycloudflare.com` URL printed in that terminal. Keep the tunnel process
running. Quick Tunnels create temporary public URLs for testing; they do not require a domain.
[Cloudflare Quick Tunnel documentation](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/)

The URL is publicly reachable, so use the demo login and synthetic records only. Close the
tunnel with Ctrl+C after the presentation.

## 5–7 minute click path and story

| Time | Click path | Story to tell |
|---|---|---|
| 0:00–0:40 | Home → point out the sample pill, four features, and demo links | “সব নাম ও সংখ্যা নমুনা”—this demo uses generated data. One document engine supports checking, history, and monitoring; escrow is separate. |
| 0:40–1:40 | Demo → case 00001 → select a finding source | Show the high-risk mismatch and the source field highlighted on the document. The result says what needs checking; it does not certify title. |
| 1:40–2:20 | Demo → case 00026 → “আগের দলিল ও প্রমাণ” → compare the two synthetic old deeds; run “সংরক্ষিত কপি যাচাই করুন” | Show the source-linked deed history and explain that SHA-256 only checks whether these stored bytes changed after upload. Government authenticity is not checked. |
| 2:20–3:00 | Demo → case 00029 → “জমির ইতিহাস” | Follow the khatian, inheritance, mutation, and proposed-sale events. Shares are taken from documents, not calculated. |
| 3:00–4:00 | Demo → Guardian → “মাসিক যাচাই চালান” | The 305 owner change is red, holding-only change on 221 is yellow, and unchanged samples stay green. New records are uploaded manually. |
| 4:00–5:00 | Demo → case 00026 → seller identity panel → create link; open it in another/private window and complete the mock verification | Explain consent, result-only storage, and that the displayed camera steps do not send or store images. Use only the synthetic seller. |
| 5:00–6:30 | Home → case 00026 escrow link → review draft, conditions, event log, mock balances, and bayna-nama PDF | Every reset starts with a new draft. Walk the condition-driven state flow; the demo bank ledger is mock money, so no real funds move. |

If a live step fails or the network is unstable, stop retrying and switch to the team's recorded
demo video on the presentation machine. The recording is not currently checked into this
repository; confirm it is available before presenting. Do not replace the fallback with real
documents or real identity data.

## If something fails

- **Docker cannot connect:** start or restart Docker Desktop, wait for its engine, then rerun
  `docker compose ps` and `docker compose up -d`.
- **Demo cases or guardian samples are missing:** run
  `docker compose exec backend python -m app.scripts.demo_reset` again. This creates another fresh
  escrow draft, archives the prior demo deal, and retains its append-only event history.
- **The frontend cannot reach the API:** check `docker compose logs frontend backend` and confirm
  the frontend container uses `BACKEND_INTERNAL_URL=http://backend:8000`; then run
  `docker compose up -d --build frontend`.
- **Tunnel does not print a URL:** confirm `http://localhost:3000` opens locally, check
  `cloudflared --version`, then try the tunnel command once more. If it still fails, use the
  recorded video.
- **Secure login cookie is missing:** confirm `COOKIE_SECURE=true` in `.env` and recreate the
  backend with `docker compose up -d --force-recreate backend`; access the public demo through
  its HTTPS tunnel URL.
