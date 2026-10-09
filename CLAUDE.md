# CLAUDE.md

Read this file before every task. It describes the project and the rules you must follow.

## What this project is

JomiGuard is a Bangladesh land-safety app. It helps a buyer check land documents before buying, and helps an owner watch their land after buying. Four features:

1. **Document check**: read uploaded land documents (khatian, deed, mutation/DCR, heir certificate), extract data, cross-check it, and report mismatches and next actions.
2. **Ownership history**: build a timeline of who owned the plot, from the same extracted data.
3. **Bayna escrow**: earnest money is held by a partner bank and released or refunded by contract conditions. The app never holds money.
4. **Probashi guardian**: keep a snapshot of each khatian, compare it with a newer copy every month, and alert on changes.

Features 1, 2 and 4 share one core engine: OCR/extraction → normalize → land case → rules. Escrow is a separate module.

## Tech stack

- Backend: Python 3.12, FastAPI, SQLAlchemy 2.0 (sync, `Mapped` style), Alembic, Pydantic v2, pydantic-settings
- Storage: Postgres 16, MinIO (documents), Redis (Celery, later)
- Frontend: Next.js (App Router, TypeScript, Tailwind)
- Tooling: uv, pytest, ruff, pre-commit, GitHub Actions
- Everything runs in Docker Compose. Hosts inside the network: `postgres`, `redis`, `minio`.

## Commands

```bash
docker compose up -d --build                      # start everything; migrations run automatically
docker compose exec backend uv run pytest -v      # run tests
docker compose exec backend uv run alembic revision --autogenerate -m "message"
docker compose exec backend uv run ruff check . && uv run ruff format .
```

## Folder layout

```
backend/app/
  core/        config, logging
  db/          base, session
  models/      SQLAlchemy models
  schemas/     Pydantic schemas (API + extracted document data)
  api/         FastAPI routers
  services/    all business logic (extraction, normalize, rules, timeline, guardian, escrow, storage)
  agent/       in-app Land AI Agent (tools, graph, prompts, guardrails)
  workers/     Celery tasks
backend/tests/ unit/, scenarios/, agent_evals/
frontend/      Next.js app
ml/            synthetic data, training, eval
docs/specs/    one spec per feature; fields.md is the field spec
docs/decisions/ why we chose a tool (ADR)
docs/legal-notes.md  verified legal facts and their sources
```

## Architecture rules

- `services/` must never import from `api/`, `agent/` or `workers/`. Those three call services, not each other.
- The extractor returns only what is printed on the document (`*_text`, names, identifiers). It never does arithmetic or unit conversion.
- `normalize.py` fills every derived field: `*_shatangsho`, `*_fraction`, `name_normalized`, ASCII digits.
- Identifiers (`dag_no`, `khatian_no`, `deed_no`, `case_no`) are always strings ("305/1" exists).
- Areas are compared in shatangsho (decimal). Keep the printed text next to every derived number.
- Supported units for now: একর, শতাংশ, decimal fractions. Other units (বিঘা, কাঠা, আনা) are kept as text and produce an `unsupported_unit` warning, never a guessed conversion.
- Field definitions live in `docs/specs/fields.md`. Follow it; if something there seems wrong, say so instead of changing it silently.

## Hard rules (never break these)

- Never write that land is "safe". No "নিরাপদ", "safe", "guaranteed" or similar in reports, findings, agent replies or UI copy. Say what matched, what did not, and what to do next.
- Never commit real documents, NID numbers, real names or real deeds. All test data is synthetic. `data/` and `.env` are gitignored.
- Never extract or store NID, phone numbers, birth registration numbers, photos or signatures.
- Never invent legal facts (inheritance shares, mutation steps, law sections). Use only what is written in `docs/legal-notes.md` or a spec. If it is missing, stop and ask.
- Every new rule needs tests. A task is not done until its tests pass.
- No secrets in committed files. Real values live in `.env`; `.env.example` uses placeholders.

## How to work

- Read the spec for the task first (`docs/specs/`).
- Only touch the files the task lists. Ask before touching others.
- Ask before adding any library that the task does not name.
- Keep changes small. Write or update tests with the code.
- When done: run the tests, then give a 3-line summary of what changed.
