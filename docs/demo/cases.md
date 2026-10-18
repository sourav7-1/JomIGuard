# Synthetic demo cases

All examples below use generated documents from `data/synthetic/cases/`.

| Case | Story | Expected result | Latest Gemini 3.5 Flash assessment |
|---|---|---|---|
| `case_00001` | Four co-owners are listed in the records; one seller offers 18 শতাংশ while the documents show 4.795 শতাংশ available to that seller. | `area_exceeds_share` (high risk); check the other co-owners' consent. | Earlier demo run found the expected area mismatch. This case was not force-refreshed in this run. |
| `case_00026` | Plain, non-family sale; three documents, no labelled mismatch. | No bad finding; low risk. | Fresh extraction of all 3 documents succeeded. Assessment: low; no bad or warning findings. |
| `case_00029` | Family/inheritance case; khatian, deed, mutation and heir certificate; no labelled mismatch. | No bad finding; low risk. | Fresh extraction of all 4 documents succeeded. Assessment: low; no bad or warning findings. |

## Refresh record — 2026-10-17

For cases 00026 and 00029, the model-specific cache entries for the clean PNGs were removed and
the extractor was called again with `gemini-3.5-flash`. All seven calls returned validated
documents and populated `data/cache/llm`. The normalized documents were passed to
`build_land_case`, `run_rules` and `assess`; both cases had no false bad findings.

The Docker backend/API was unavailable during this refresh, so these results are in the shared
LLM cache and were assessed through the same extraction/normalization/rules services locally;
new database extraction rows were not written. `demo_reset` seeds these generated case images and
creates a fresh draft escrow deal for case 00026 each time it runs.
