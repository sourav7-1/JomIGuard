# JomiGuard

JomiGuard is a Bangladesh land-document review and monitoring demo. It helps people compare
information printed on land records, see a document-based ownership timeline, and monitor a
khatian after purchase. It reports what matched, what did not, and what to check next; it is not
a legal opinion or a title guarantee.

## Four connected features

- **Document check:** upload khatian, deed, mutation/DCR, and heir-certificate copies; review
  extracted fields, sources, mismatches, and suggested next steps.
- **Ownership timeline:** view record, sale, mutation, inheritance, and proposed-sale events from
  the case documents.
- **Bayna escrow:** follow agreement, deposit, conditions, registration, release, or refund. The
  demo bank is a mock; in a real deployment a bank partner would handle funds.
- **Probashi guardian:** compare a saved khatian snapshot with a newer copy uploaded by hand and
  review any changes.

Seller verification is a separate mock e-KYC flow attached to a case. It checks a seller name for
the demo and stores only the result; it does not collect or store NID images, selfies, phone
numbers, signatures, or NID numbers.

## Previous deed archive

Open case 00026 and choose **আগের দলিল ও প্রমাণ** to see the synthetic deed documents linked to
that land, compare extracted deed fields, open the source page, and check the stored file's
SHA-256 fingerprint. A matching fingerprint only means the stored bytes match their upload-time
baseline. It does not establish that a deed is genuine or prove ownership. Official source
verification is not connected; the page says so explicitly.

## Architecture

```mermaid
flowchart LR
  Browser[Next.js web app] -->|same-origin /api/*| Next[Next.js rewrite]
  Next --> API[FastAPI]
  API --> DB[(PostgreSQL)]
  API --> Files[(MinIO documents)]
  API --> Queue[Redis]
  Queue --> Worker[Celery extraction worker]
  Worker --> Files
  Worker --> DB
  API --> Rules[Normalize and rule engine]
  Rules --> DB
  API --> MockIdentity[Mock identity provider]
  API --> MockBank[Mock escrow bank]
  Queue -->|satellite queue| SatWorker[Celery satellite-worker]
  SatWorker -->|POST /api/analyze-area| Sentinel[Sentinel service: Flask + U-Net]
  Sentinel --> EE[Google Earth Engine: Sentinel-1/2]
  SatWorker --> DB
```

The API and both workers run in Docker Compose. The browser talks only to Next.js at `/api`;
Next.js forwards those requests to `BACKEND_INTERNAL_URL`. Satellite checks take about a minute,
so they have their own queue and worker (`satellite-worker`, one check at a time); document
extraction on the default queue is never blocked by them.

## Satellite check

On a case page, draw the plot outline on the map and run **স্যাটেলাইট যাচাই করুন**. The sentinel
service builds a February (dry-season) Sentinel-1/2 composite for every year from 2019 to 2025
and measures tree cover and standing water. The findings compare this with the khatian. For
example, a plot recorded as cropland (নাল) that has water around it in the dry season gets a
finding, and so does water that rises year after year (possible river erosion). Each finding has
a next step. Satellite findings are a separate group: they never change the document risk level.

- **Surroundings, not the plot.** Pixels are 10 m, so results describe roughly 200 m around the
  plot, not the area inside its boundary. Every finding says so.
- **Demo case.** `demo_reset` adds a synthetic Bhola case (মৌজা চর মেঘনা, দাগ ৪১৭) on an eroding
  Meghna bank. It replays a recorded real result
  (`backend/app/scripts/demo_data/satellite_bhola.json`), so its findings show without waiting.
  The script prints the case link.
- **Setup for new checks.**
  1. Download the trained model (see step 3 of [Run locally](#run-locally)).
  2. Copy `sentinel/.env.example` to `sentinel/.env` and set `EARTH_ENGINE_PROJECT_ID` to your
     Google Earth Engine project.
  3. Run `earthengine authenticate` once on this computer. Docker mounts the login into the
     sentinel container.

  The Bhola demo case works without Earth Engine.

## Run locally

1. Install Docker Desktop and start it.
2. Copy `.env.example` to `.env`, set unique local values for the database, MinIO, admin login,
   and `SESSION_SECRET`. Keep `COOKIE_SECURE=false` for plain `http://localhost` development.
   For the satellite check, also create `sentinel/.env` (see [Satellite check](#satellite-check)).
3. Download the trained satellite model. `segmentation_10band.pt` is not in git (pre-commit
   blocks large files); get it from the GitHub release `model-v1` into `sentinel/models/`:

   ```powershell
   Invoke-WebRequest https://github.com/sourav7-1/JomIGuard/releases/download/model-v1/segmentation_10band.pt -OutFile sentinel\models\segmentation_10band.pt
   Get-FileHash sentinel\models\segmentation_10band.pt
   ```

   The SHA-256 must be
   `3bacb3eb3f5bbaa96d195c71520a1784f96b8cf57b599416b65d0ba85a026855`.
4. From the repository root, run:

   ```powershell
   docker compose up -d --build
   docker compose exec backend python -m app.scripts.demo_reset
   ```

5. In a second terminal:

   ```cmd
   cd frontend
   set BACKEND_INTERNAL_URL=http://localhost:8000
   npm run build && npm start
   ```

6. Open `http://localhost:3000` and sign in with `ADMIN_USERNAME` and `ADMIN_PASSWORD` from
   `.env`.

For the timed presentation and temporary public tunnel, use
[docs/demo/runbook.md](docs/demo/runbook.md).

## Privacy and demo boundaries

- Demo records and names are synthetic. Do not upload real documents to this demo.
- Never store NID numbers, NID images, selfies, face data, phone numbers, birth-registration
  numbers, or signatures. Identity storage contains verification results only.
- Gemini free-tier requests may be used to improve Google's models. Send synthetic documents
  only; never send real user documents.
- Identity verification and escrow funds are simulated. The app does not perform real e-KYC or
  hold or transfer real money.
- Findings are document checks and do not establish legal title, possession, encumbrances, or
  court status.

## Known limits

- OCR and extraction can misread scans; review source fields and the original page.
- Fingerprints detect changes to stored copies only. Government or licensed deed verification is
  not connected, and older documents without an upload-time fingerprint cannot be verified against
  their original upload.
- Timeline events and shares come from extracted text. Inheritance shares are not calculated.
- Guardian changes appear only when a newer khatian is uploaded; there is no email alert or
  automatic registry polling.
- The public Cloudflare Quick Tunnel is temporary and intended for testing, not production.
- A synthetic demo video is not stored in this repository; keep the team's recording available
  on the presentation machine as the live-demo fallback.

© 2026 Sourav Kundu Samya. All rights reserved.
