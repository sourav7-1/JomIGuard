# Phase 2 review (days 13–24)

**Date:** 2026-10-15. **Scope:** status only; no code was changed for this review.
**Verdict:** the building blocks exist and are tested, but **the Phase 2 milestone is not met and
not yet measurable**: the LLM extractor has never been run, and the running stack currently
rejects every upload because of an unmigrated model change.

## 1. Tests and lint

| check | result |
|---|---|
| backend tests (Docker, `uv run pytest`) | **365 passed**, 0 failed |
| ml tests (Linux container `mlbox`, PYTHONPATH=backend) | **146 passed**, 0 failed |
| ruff check, backend and ml | clean |
| ruff format, ml | clean |
| ruff format, backend | **1 file differs**: `app/models/document.py` line 45 |

The format difference comes from two ruff versions: the project pins 0.16.10 (Docker), while
`uvx ruff` on the host is 0.17.0. Pick one version (pre-commit should use the pinned one).

Note: the backend tests build their tables with `Base.metadata.create_all`, not with Alembic.
They therefore pass even when a model and the migrations disagree (see section 4).

## 2. Milestone: extraction accuracy (eval_v2, test split, 141 images)

Target: critical-field accuracy **≥ 90 % on clean** and **≥ 80 % on augmented** images.

| run | extractor | critical clean | critical augmented | accuracy (= recall) | precision | mean CER | cost / doc | s / doc |
|---|---|---|---|---|---|---|---|---|
| oracle (sanity) | ground truth copied | 100 % | 100 % | 100 % | 100 % | 0.000 | – | – |
| empty (sanity) | doc_type only | 0 % | 0 % | 3.0 % | 100 % | 1.000 | – | – |
| **A** | Tesseract + regex | **73.5 %** | **18.0 %** | 38.5 % | 89.9 % | 0.670 | $0.00 | 1.9 |
| B–F | LLM variants | not run | not run | – | – | – | – | – |

- **Milestone: not met.** The only real extractor measured (A) is far below target on augmented
  images. The LLM extractor (`services/extraction/llm.py`) is built and unit-tested with a mocked
  client, but has **never been called**: `.env` has no `ANTHROPIC_API_KEY`, `LLM_MODEL`, prices
  or `LLM_DAILY_BUDGET_USD`.
- Run A by document type (critical accuracy): deed 49 %, heir certificate 43 %, khatian 34 %,
  mutation 33 %. Weakest critical fields: `dcr.dcr_date` 0 %,
  `heir_cert.deceased_address.district` 0 % (regex bug: "জেলা" also matches inside "উপজেলা"),
  `heir_cert.heirs[].father_or_husband_name` 0 % (see risk 6), schedule dag/area on deeds 12–15 %.
- **Calibration: not available.** There are no per-field confidence levels ("high" fields), so
  the accuracy of high-confidence fields, the share of flagged fields and the errors caught by
  flags cannot be measured. Today the only flags are normalize warnings (`field_flags`).

## 3. Document-type classifier (`services/classify.py`)

| measure | result |
|---|---|
| test split + 40 "other" images (181 images) | **100 %** accuracy |
| per class precision / recall | 100 % / 100 % for all five classes |
| worst confused pair | none on test (train: 1 heavy mutation → "other", 99.8 %) |
| "other" false accepts (other images taken as a land document) | **0 of 40** |
| heavy augmented images | 100 % (22 images) |

Report: `data/eval/classify/report.md`. Keywords and thresholds were tuned on the train split
only. These numbers come from synthetic pages with one layout per type and an identical footer;
treat them as an upper bound, not as real-world accuracy.

## 4. End-to-end smoke test

Uploads of one clean khatian, deed, mutation, heir certificate and "other" image through
`POST /documents` (no `doc_type`) all **failed with HTTP 500**, so no document reached the
worker:

| image | upload | final status | detected_doc_type | extraction |
|---|---|---|---|---|
| khatian_00002.png | 500 | – | – | – |
| case_00001/deed.png | 500 | – | – | – |
| case_00001/mutation.png | 500 | – | – | – |
| case_00001/heir_cert.png | 500 | – | – | – |
| other_00002.png | 500 | – | – | – |

**Cause:** `backend/app/models/document.py` was edited at 21:20 (after the Celery pipeline task)
to add `current_step` (new `DocStep` enum) and `updated_at`. There is no Alembic migration for
them, so every insert fails: `column "current_step" of relation "documents" does not exist`.
Nothing else in the code uses these fields yet; it looks like unfinished day-22 work.

Even after a migration, the stack as configured would mark every document `failed`: the worker
defaults to `EXTRACTOR=llm`, and the LLM settings are missing (the pipeline stores a clear
"LLM settings missing" error). Before the model change, the same pipeline with
`EXTRACTOR=tesseract_regex` processed a clean khatian end to end: status `done`, detected
`khatian` (confidence 1.0), extraction `ok`, owner share_shatangsho 4.4 (same as ground truth).

## 5. Roadmap coverage (days 13–24)

| day | topic | state | proof |
|---|---|---|---|
| 13 | preprocess | **done** | `services/preprocess.py`, `tests/unit/test_preprocess.py`, `ml/eval/preprocess_preview.py` |
| 14 | OCR | **done** | `services/ocr.py`, `tests/unit/test_ocr.py`, `ml/eval/ocr_preview.py` (grid), `data/preview/ocr/grid.md`, Dockerfile (tessdata_best) |
| 15 | normalize | **done** | `services/normalize.py`, `tests/unit/test_normalize.py` (round trip over all samples and scenarios), `ml/tests/test_normalize_vs_generator.py` |
| 16 | extraction eval | **done** | `ml/eval/compare.py`, `ml/eval/extraction.py`, `ml/tests/test_eval_extraction.py`, `data/eval/baseline_*` |
| 17 | LLM extraction | **partial** | code and mocked tests (`services/extraction/{llm,prompts,budget,base}.py`, `tests/unit/test_llm_extractor.py`, `ml/eval/run_extractor.py`); never run, no report |
| 18 | extractor comparison | **partial** | run A only (`services/extraction/tesseract_regex.py`, its tests, `data/eval/A_tesseract_regex_test`); missing: `ml/eval/make_dev_set.py`, runs B–F, prompt tuning, `docs/decisions/extraction.md` |
| 19 | retries / flags | **missing** | no retry on invalid LLM output, no per-field confidence; only normalize warnings as `field_flags` |
| 20 | classifier | **done** | `services/classify.py`, `tests/unit/test_classify.py`, `ml/synth/other.py`, `ml/eval/classify_eval.py`, `data/eval/classify/report.md` |
| 21 | Celery pipeline | **done, currently broken** | `services/pipeline.py`, `app/workers/`, migration `a316897d7cb5`, `tests/unit/test_pipeline.py`, worker in `docker-compose.yml`; uploads fail since the unmigrated model change |
| 22 | status API | **partial** | `GET /documents/{id}` returns the processing fields; `current_step` / `updated_at` started in the model only (no migration, not set by the pipeline); no endpoint for extraction data |
| 23 | error analysis | **missing** | no analysis document; `errors.csv` exists only for run A |
| 24 | review | this file | `docs/reviews/phase-2.md` |

## 6. Housekeeping

| item | state |
|---|---|
| git | **57 uncommitted paths** (25 modified, 8 staged new, 30 untracked, incl. `AGENTS.md`); last commit `a5f4fa3` on 2026-10-10. Days 13–23 exist only in the working tree. |
| `docs/devlog.md` | one entry (2026-10-09); **no entries for days 13–23** |
| `docs/legal-notes.md` | **empty** (0 bytes) |
| `docs/decisions/` | **empty** (only `.gitkeep`); no ADR for OCR settings, extractor choice or Celery |
| CLAUDE.md | lists the Docker and dataset **v1** commands; does **not** list the worker/pipeline, `EXTRACTOR`, the eval commands (`ocr_preview`, `extraction`, `run_extractor`, `classify_eval`), dataset v2, or how ml tests run on Linux (pydantic is blocked by Smart App Control on Windows). It does include the new rule "OCR input is `preprocess(...).gray`". |
| LLM spend | **$0.00**: no budget file (`data/llm/spend.json`) and no LLM cache exist; no LLM call has been made |
| `AGENTS.md` | untracked copy of the project instructions, not created by these tasks; possibly from another agent tool, which may also explain the unmigrated model edit |

## 7. Risks for Phase 3 (rule engine)

1. **No trustworthy extraction yet.** The rules compare owner names, shares, dag numbers and
   areas: exactly the critical fields. The only measured extractor gets 18 % of them right on
   photos. Until the LLM runs are done (or the baseline improves a lot), rule results on real
   uploads would mostly reflect extraction errors.
2. **Upload path broken and migrations unchecked.** Model edits without migrations break
   production while tests stay green. Add a test that runs `alembic upgrade head` and compares
   with the models (e.g. `alembic check`), and finish or revert the `current_step` change.
3. **Default extractor not configured.** `EXTRACTOR=llm` without LLM settings fails every
   document. Decide the default (ADR) and document it in CLAUDE.md and `.env.example`.
4. **No legal facts recorded.** `docs/legal-notes.md` is empty, and CLAUDE.md forbids inventing
   legal facts. Rules that need them (`heir_consent_missing`, Decision 3 "one share per
   khatian", Decision 5 "heir shares from the mutation") are marked "needs expert check" and
   cannot be finalised.
5. **Synthetic-only evidence.** One layout per document type, clean fonts and a shared footer;
   the classifier's 100 % and normalize's round trips say little about real scans. All fields in
   `fields.md` are still UNVERIFIED.
6. **Ground-truth convention for heirs.** The generator fills
   `heirs[].father_or_husband_name` with the deceased's name, although the heir table does not
   print it. Either the extractor should infer it (against "only what is printed") or the ground
   truth should drop it; today it counts as a miss for every extractor.
7. **OCR layout fragility.** Tesseract psm 3 sometimes reads only the footer of a photographed
   table; the classifier and the baseline work around it with a second psm. Any OCR-dependent
   step (including an "OCR text as hint" LLM option) inherits this.
8. **Lost decimal points.** OCR drops the leading "." of shares and areas (".২৫০" → "২৫০"); the
   baseline restores it heuristically. A wrong share or area directly changes
   `area_exceeds_share`.
9. **Review status is coarse.** An extraction is `needs_review` only for normalize warnings or a
   label mismatch; there is no field confidence, so the rule engine cannot tell weak values
   from strong ones (day 19).
10. **Architecture-rule exception.** `api/documents.py` imports `workers/tasks.py` (as that task
    asked), against CLAUDE.md "api/, agent/ and workers/ call services, not each other". Settle
    it before more cross-calls appear.
11. **Large uncommitted state.** Two weeks of work live only in the working tree; one bad
    checkout loses it. Commit in reviewed steps.
