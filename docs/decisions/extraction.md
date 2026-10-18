# Extraction evaluation — measured on a 20-image sample

**Status: partial.** Date: 2026-10-17. Dataset: synthetic v2 test split, fixed stratified sample
in [`ml/datasets/sample_v2.json`](../../ml/datasets/sample_v2.json). Gemini run pinned to
`gemini-3.5-flash`.

## Results so far

| Measure | Tesseract + regex | Gemini 3.5 Flash |
|---|---:|---:|
| Sample images | 20 / 20 | 18 recorded / 20 requested |
| Successful reads | 20 | 11 |
| Provider errors | 0 | 7 HTTP 429 |
| Missing predictions | 0 | 2 (one connection error; one not attempted) |
| Critical-field accuracy, all presets | 38.7% | 48.2% |
| Critical accuracy, clean | 77.2% | 95.6% |
| Critical accuracy, augmented | 14.6% | 18.5% |
| Mean latency per recorded image | 1.73 s | 35.07 s |
| Configured cost | $0.00 | $0.00 |
| E2E false-bad rate | 0 / 2 clean cases | not measured |

Gemini accuracy above includes all 20 sample rows; failed and missing predictions count as
unread fields. Of the 18 rows returned by the run, 11 extracted successfully and 7 became error
results after repeated 429s. The next request failed with a network connection error, so the
runner stopped on a connection error for `case_00048_heir_cert_0`; it did not attempt the final
image, `khatian_00012_khatian_1`. Do not read these partial sample metrics as a completed
benchmark. The 429 backoff time is included in Gemini latency.

The recorded overall critical-field count is 535: 206 clean and 329 augmented. Gemini scores by
preset: clean 95.6% (206 fields), light 25.2% (123), medium 21.8% (110), heavy 6.3% (96).
Tesseract scores on the same fixed sample: clean 77.2%, light 20.3%, medium 14.5%, heavy 7.3%.
Gemini's configured token prices are zero for this free-tier run; measured cost therefore shows
$0.00.

Gemini's end-to-end four-case run is still pending. Fresh Gemini 3.5 Flash extractions for the
two clean demo cases, `case_00026` and `case_00029`, were assessed separately through normalize,
land-case construction and rules: both had low risk and no bad findings. This is not the same as
the four-case E2E sample result.

## Handwritten (synthetic, n=pending)

Basic handwritten deed support records a handwritten flag and lowers each extracted field's
confidence by one level. The expected paired photos and hand-written ground truth are not present
in `data/handwritten/` in this workspace, so no accuracy or latency measurements are available.
Once synthetic pairs are added, run from `ml/` with `LLM_PROVIDER=gemini`:

```bash
PYTHONPATH=../backend uv run python -m eval.extraction --handwritten-dir ../data/handwritten
```

The evaluator writes `data/eval/handwritten_gemini_current/`; add its measured n, field accuracy,
critical accuracy, and seconds per document here. Never evaluate real handwritten documents on
Gemini free tier.

## Artifacts and reproduction

- Fixed sample: `ml/datasets/sample_v2.json`.
- Gemini predictions, including error results: `data/predictions/gemini_35_flash_sample_v2/`.
- Gemini partial report: `data/eval/gemini_35_flash_sample_v2/report.md` and `report.json`.
- Tesseract comparison: `data/eval/tesseract_sample_v2/report.md`.
- Tesseract E2E baseline: `data/eval/e2e_tesseract_sample_v2/report.md`.
- Demo refresh details: [`docs/demo/cases.md`](../demo/cases.md).

Commands from `ml/` (set `GEMINI_MODEL=gemini-3.5-flash` and `LLM_PROVIDER=gemini` in the
environment before the Gemini command):

```bash
PYTHONPATH=../backend uv run python -m eval.run_extractor \
  --extractor llm --sample datasets/sample_v2.json --name gemini_35_flash_sample_v2
PYTHONPATH=../backend uv run python -m eval.run_extractor \
  --extractor tesseract_regex --sample datasets/sample_v2.json --name tesseract_sample_v2
PYTHONPATH=../backend uv run python -m eval.e2e_cases \
  --extractor tesseract_regex --sample datasets/sample_v2.json --name e2e_tesseract_sample_v2
```

The Gemini E2E run and the two missing image predictions need a working Google API connection.
Successful extractions are in the LLM cache and will be cache hits on retry; provider errors are
not cached and will call the API again.
