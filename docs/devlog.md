# Devlog

## 2026-10-09

- Added Pydantic schemas for extracted document data (`backend/app/schemas/extracted.py`): `KhatianData`, `DeedData`, `MutationData`, `HeirCertData`, combined as `ExtractedDocument` (discriminated on `doc_type`).
- Added one synthetic sample per document type (`backend/tests/fixtures/samples/`) and schema tests.
- Synced `docs/specs/fields.md` with the code: `filled_by` column, `DCRData` → `MutationData`, helper models `KhatianRef` / `PriorDeed` / `Address` documented, `name_normalized` added to `Owner` and `Heir`.
- **Decisions:** from 2026-10-09, `docs/specs/fields.md` and `app/schemas/extracted.py` are in sync. The MVP rules in the spec's "Decisions (MVP)" section apply from this date.
- Open: fields such as dates, `price_taka`, `fee_taka`, `relation` and ASCII-digit identifiers are marked `extractor`, but they are conversions. Decide extractor vs `normalize` before writing `normalize.py`.
