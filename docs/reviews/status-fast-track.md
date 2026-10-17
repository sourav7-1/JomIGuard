# Status check before the fast track to a demo

**Date:** 2026-10-16. **Verdict:** the backend flow works end to end (upload → classify →
extract → assess → correct → re-assess → PDF), **but not with the stack as configured**, and the
case page in the frontend is a static mockup. Three things block a real demo; they are listed in
section 4.

## 1. Tests and lint

| check | result |
|---|---|
| backend tests (Docker) | **589 passed, 1 failed** (`test_scenario[18_dag_and_area_mismatch]`, open decision, see 4.4). A first full run also failed 13 pipeline/report tests; they pass alone, together, and in a second full run → **flaky shared test database** (see 4.6). |
| ml tests (Linux container `mlbox`) | **150 passed** |
| ruff backend | clean (fixed: unused `d3` in `tests/unit/test_documents_api.py`, formatting of `app/main.py`) |
| ruff ml | clean |
| frontend `npm run lint` | clean |
| frontend `npm run build` | succeeds (13 routes) |

## 2. Feature status

| item | status | proof |
|---|---|---|
| a. LLM extraction on real images (Day 17) | **missing (blocked)** | Code and mocked tests exist (`tests/unit/test_llm_extractor.py`). No test-split run: no `data/eval/llm_*`, no spend file, no cache. In the demo walk every extraction failed with `api: AuthenticationError`. **Cause: `.env` defines the LLM keys twice**; lines 19–26 are the placeholders from `.env.example` (`ANTHROPIC_API_KEY=your_api_key_here`, `LLM_MODEL=model_id_here`, prices 0) and override lines 13–17. The key on line 13 is also only 10 characters long and both prices there are empty. Not edited (secrets file). |
| b. Extractor comparison + ADR (Day 18) | **partial** | Run A (Tesseract + regex) only: `data/eval/A_tesseract_regex_test` (critical 73.5 % clean / 18.0 % augmented). No runs B–F, no `ml/eval/make_dev_set.py`, **no `docs/decisions/extraction.md`** (`docs/decisions/` is empty). |
| c. Retries + confidence flags (Day 19) | **missing** | No retry on invalid LLM output; no per-field confidence. `field_flags` hold normalize warnings and `["human"]` for confirmed fields (`services/corrections.py`). No calibration numbers. |
| d. Document classifier (Day 20) | **working** | `data/eval/classify/report.md`: test split + 40 "other" images, 181 images, **100 %**, no confused pair, **0 / 40 "other" false accepts**. In the demo walk all 4 documents were classified correctly. |
| e. Celery pipeline + status API (Day 21–22) | **working with `EXTRACTOR=tesseract_regex`**, failing with the configured LLM | Demo walk (below): 4 uploads without `doc_type` → all `done`, correct `detected_doc_type`, extractions stored. With the default worker: all `failed` (AuthenticationError). Status API: `GET /documents/{id}` (`DocumentStatusOut`, `current_step`), `GET /lands/{id}/documents`, `/lands/{id}/case-view`. |
| f. Error analysis, eval_v2 (Day 23), Phase 2 review (Day 24) | **partial** | `docs/reviews/phase-2.md` exists. eval harness + v2 baselines exist (`data/eval/baseline_*`). **No error-analysis document** and no LLM errors to analyse. |
| g. PDF report fixes | **working** | `tests/unit/test_report.py::test_text_layer_is_copyable` (ActualText; exact words extracted), `test_one_check_line_per_rule` (9 ✓ for scenario 01), labelled sources and "১৫ শতাংশ (.১৫০০ একর)"; sample `docs/samples/report-scenario-01.pdf` (2 pages). |
| h. e2e evaluation + Phase 3 review (Day 32) | **working** | `ml/eval/e2e_cases.py`, `data/eval/e2e_v1/report.md` (Tesseract: detection 67 %, false alarms 40 %); ground truth 100 % / 0 % (`ml/tests/test_e2e_cases.py`); `docs/reviews/phase-3.md`. |
| i. Frontend (Day 33–36) | **partial** | App shell, header, journey rail, theme toggle: working. **Upload flow: working** (creates the land, uploads with progress, polls status, reprocess, "assess" button → `POST /lands/{id}/assess`). **Case page `/cases/[id]`: static mockup**: verdict, ✓ items, findings and checklist come from fixed strings in `lib/strings.ts` (রহিম, দাগ ৩০৫, ৬/১০ শতাংশ) for every case, not from the assessment. **No correction UI and no PDF link** in the frontend (the backend endpoints exist). |

## 3. Demo flow (the main result)

Stack: backend, worker, Postgres, Redis, MinIO (Docker), frontend `next start` on :3000. Case
documents: synthetic `case_00001` (family case, label `area_exceeds_share`: শেখ কামাল সরকার owns
15.17 শতাংশ, deed sells 18), uploaded **without** `doc_type`. Steps were driven through the same
API calls the frontend makes; the case page was opened in Chrome.

| step | with the configured worker (`EXTRACTOR=llm`) | with `EXTRACTOR=tesseract_regex` |
|---|---|---|
| 1. create case `POST /lands` | 201 | 201 |
| 2. upload 4 documents | 4 × 201 | 4 × 201 |
| 3. all processed | **all 4 `failed`**: "কাগজ থেকে তথ্য পড়া যায়নি: api: AuthenticationError" (classifier was right for all 4) | all 4 `done`, detected khatian / deed / dcr / heir_cert |
| 4. assess `POST /lands/{id}/assess` | not reached (nothing to assess) | 201, **high**: `area_exceeds_share` (the labelled one: "খতিয়ানে শেখ কামাল সরকার-এর অংশ ১৫.১৭ শতাংশ, কিন্তু দলিলে ১৮ শতাংশ …") plus 3 false findings from OCR errors (`dag_mismatch`, `area_sum_mismatch`, `heir_missing_from_mutation` for a name read as "মোছাঃ জরিনা আক্তার a") |
| 5. findings shown in the UI | – | **breaks**: `/cases/{id}` renders (200, no console errors) but shows the static demo text (রহিম, দাগ ৩০৫, BS ৮৮২), not this case |
| 6. correct one field | – | API works: `PATCH /documents/{id}/extraction` `heirs[3].name` → 200 (new extraction row). **No UI for it.** |
| 7. re-assess | – | 201, `heir_missing_from_mutation` gone (findings: dag, area_sum, area_exceeds) |
| 8. PDF | – | `GET …/report.pdf` → 200, 33.7 KB, `%PDF`. **No link in the UI.** |

CORS for `http://localhost:3000` is set; all frontend routes return 200.

## 4. Must fix before new features (in order)

1. **`.env` LLM settings** (owner: you, 5 minutes). Remove the duplicated placeholder block
   (lines 19–26), put the real key on one line, set `LLM_PRICE_INPUT_PER_MTOK` and
   `LLM_PRICE_OUTPUT_PER_MTOK`. Until then every upload fails. For a demo without the API, set
   `EXTRACTOR=tesseract_regex` (expect OCR false alarms).
2. **Case page from real data** (frontend, ~1 day). `/cases/[id]` must load
   `GET /lands/{id}/assessments/latest` (or `/case-view`) and render headline, summary, ✓ list
   (`passed`), findings with `message_bn` and labelled sources, coverage and actions; add a PDF link
   (`/lands/{id}/assessments/{aid}/report.pdf`) and a field-correction form on
   `PATCH /documents/{id}/extraction` followed by re-assess.
3. **One real LLM run** on the test split (`eval.run_extractor --limit 10`, then all), to know
   whether extraction errors (40 % false alarms with Tesseract) drop enough for a credible demo;
   then the ADR `docs/decisions/extraction.md`.
4. **Scenario 18 decision** (consent on the whole-khatian comparison) → 20 / 20.
5. **Day 19** retries + confidence flags, so OCR-like slips become "নিজে মিলিয়ে নিন" items rather
   than findings (the demo case showed 3 false findings).
6. **Flaky backend tests**: all runs share `jomiguard_test` and drop/create its tables; two
   concurrent runs (e.g. two agents) break each other. Use a per-run database or schema.

## 5. Uncommitted work and commits

102 paths uncommitted; last commit `b6ce888`. Several files are partly staged, so start from a
clean index. Run from the repo root (bash). Intermediate commits may not pass the full suite on
their own (the lands API imports the report); run the tests after the last commit.

```bash
git reset   # unstage everything; the working tree is unchanged

# 1. Rule engine and rules
git add backend/app/services/rules backend/app/schemas/land_case.py \
  backend/tests/test_scenarios.py backend/tests/unit/test_rule_*.py backend/tests/unit/test_names.py \
  docs/specs/rules.md
git commit -m "Rules: engine, identity, area, heirs and chain rules with scenario harness"

# 2. Assessment, next actions and the Bangla PDF report
git add backend/app/services/risk.py backend/app/services/actions.py backend/app/services/report.py \
  backend/app/schemas/assessment.py backend/app/models/assessment.py backend/app/models/__init__.py \
  backend/alembic/versions/229c6bc6c37e_assessments.py backend/app/report backend/app/scripts \
  backend/Dockerfile backend/pyproject.toml backend/uv.lock \
  backend/tests/unit/test_risk.py backend/tests/unit/test_actions.py backend/tests/unit/test_report.py \
  docs/specs/actions.md docs/legal-notes.md docs/samples
git commit -m "Assessment: risk, next actions and Bangla PDF report (WeasyPrint, copyable text)"

# 3. Status API, corrections and field metadata
git add backend/app/api backend/app/main.py backend/app/core/config.py \
  backend/app/schemas/document.py backend/app/schemas/extraction.py backend/app/schemas/field_meta.py \
  backend/app/services/corrections.py backend/app/services/pipeline.py \
  backend/tests/unit/test_documents_api.py backend/tests/unit/test_pipeline.py \
  backend/tests/unit/test_corrections.py backend/tests/unit/test_lands_api.py \
  backend/tests/unit/test_meta_api.py .env.example
git commit -m "API: document status, land case view, extraction corrections and field metadata"

# 4. Frontend
git add frontend
git commit -m "Frontend: app shell, upload flow, case page mockup"

# 5. ML evaluation and reviews
git add ml/eval/e2e_cases.py ml/eval/scenario_report.py ml/tests/test_e2e_cases.py docs/reviews
git commit -m "Eval: end-to-end cases, scenario report, Phase 3 and fast-track reviews"

# 6. Identity spec and hard rule
git add docs/specs/identity.md CLAUDE.md
git commit -m "Docs: identity verification spec; hard rule on identity data"

git status   # should be clean
docker compose exec backend uv run pytest -q
```

## 6. Notes from this check

- Small fixes made: unused `d3` in `backend/tests/unit/test_documents_api.py`; `ruff format` of
  `backend/app/main.py`.
- `backend/app/services/corrections.py` raises FastAPI `HTTPException` inside a service. This
  doesn't break the CLAUDE.md import rule (services must not import `api/`, `agent/` or
  `workers/`), but it ties a service to HTTP. Worth moving to the API layer later.
- The demo worker and the Next.js server used for this check were stopped afterwards (port 3000
  freed); the regular worker is running again.
