# Previous deed archive

The archive reuses the existing `documents` and `extractions` records. A deed stays linked to its
land; each extraction run remains in extraction history. Document creation time and uploader
identify when and by whom the source was added. No second deed metadata table is maintained.

At upload, the backend stores SHA-256 of the exact bytes written to MinIO on `documents`.
`POST /documents/{id}/fingerprint/verify` reads the currently stored bytes and compares their
fingerprint with that upload baseline. Older rows with no baseline return an unknown result and
are not silently treated as unchanged. A changed result does not rewrite the original baseline.

`GET /lands/{id}/deeds` lists the land's extracted deed documents and compares the printed deed
number, date, type, parties, mouza, plot numbers and printed areas against the prior deed in date
order. Every item points to its source document. The timeline already reads all deed documents
linked to the land and uses their extracted dates and parties; no shares are calculated here.

SHA-256 detects changes to the copy stored by this application only. It does not establish a
document's authenticity, government registration, or legal ownership. No government registry or
licensed verification provider is connected, so the API and page always state that official
authenticity has not been checked.

The demo reset adds two invented synthetic deed pages for case 00026. They are stored as ordinary
documents with `seed` extractions, source bytes and upload fingerprints. Stable document IDs make
the seed repeatable; prior rows are kept. Do not use real deeds or identity data in the demo.

Each document reuses `owner_id` and `created_at` as uploader and upload time. `source_type` records
`user_upload` or a user's unverified claim that a copy is certified; `official_source` is rejected
until an authorised connector exists. Extraction rows record `created_by` (`ai`, `seed`, or the
user ID). The migration adds an append-only audit table for upload, provenance, correction and
confirmation events. Run `python -m app.scripts.backfill_document_fingerprints` after migration to
fingerprint existing MinIO objects; rows without a baseline remain explicitly unknown until then.

`GET /lands/{id}/deeds/compare?a=&b=` compares printed extracted fields and reports simple links
between records. It adds no rule-engine findings and does not establish a legal ownership chain.
The UI always says that government sources have not been checked. The fingerprint only detects
whether the stored bytes differ from the recorded baseline; it does not prove title or document
status. Obtain and compare certified copies with the sub-registry office; this advice is marked
for legal/office verification in `docs/legal-notes.md`.
