# Rule specification

**Status: DRAFT.** Rules live in `backend/app/services/rules/` (one file per group; a rule is a
`@register`-ed class). They read a `LandCase` (`schemas/land_case.py`) and return results with
Bangla messages and source references; codes and severities come from `findings.md`. A rule whose
required roles are missing is **skipped** by the engine; a value that cannot be read gives a
**skipped** result, never a finding (findings.md, general rules).

Roles used below: *proposed deed* = the draft deed (or the latest registered deed if there is no
draft), *current khatian* = the khatian of the newest survey (BS/CITY > RS > SA > CS).

## Name matching (`rules/names.py`)

Used by `seller_is_owner` and `seller_father`. Names are compared on `name_normalized`
(honorifics already removed), after `match_key`: NFC, zero-width characters removed, ী→ি and
ূ→ু folded, spaces collapsed. Then **token by token**, never as one whole string:

| constant | value | meaning |
|---|---|---|
| `TOKEN_MIN` | 85 | every aligned token pair needs rapidfuzz ratio ≥ 85 |
| `FIRST_TOKEN_MIN` | 90 | the first token (given name) needs ≥ 90 |
| `MAX_TOKEN_DIFF` | 1 | token counts may differ by one, and only by a missing **middle** token |

| a | b | match | why |
|---|---|---|---|
| রহিম উদ্দিন | রহিম উদ্দীন | yes | ী folded to ি |
| মোহাম্মদ আব্দুল করিম | মোহাম্মদ করিম | yes | one middle token missing |
| রহিম উদ্দিন | করিম উদ্দিন | **no** | first token 75 < 90 (a whole-string score would be > 80) |
| সালমা খাতুন | সালমা বেগম | no | last token differs |
| রহিম | রহিম উদ্দিন | no | a missing first or last token is not allowed |

Known limits: nicknames, initials ("মো. আ. করিম"), and transliteration between Bangla and
English are not handled; two different people with identical names and fathers cannot be told
apart (see `seller_father`).

## `plots_on_khatian` → `dag_mismatch` (bad)

- **Compares:** every `schedule_plots[].dag_no` of the proposed deed with the `plots[].dag_no`
  of the current khatian, after `normalize_identifier` ("৩০৫" = "305"; "305/1" is a string).
- **Roles:** proposed deed, current khatian. One result per schedule dag.
- **Pass:** deed dag 305, khatian dags 305, 306 → "দলিলের দাগ ৩০৫ বর্তমান খতিয়ান (BS ৮৮২)-এ আছে।"
- **Fail:** deed dag 306, khatian dag 305 → "দলিলে দাগ ৩০৬, কিন্তু বর্তমান খতিয়ান (BS ৮৮২)-এ দাগ ৩০৫ …"
- **Skipped:** no dag number could be read in the schedule.
- **Known limits:** dag numbers can change between surveys; this rule only compares with the
  current khatian (needs expert check). A deed that names an older survey's dag (e.g. an SA dag
  next to an SA khatian number) will be reported as a mismatch.

## `khatian_refs` → `khatian_mismatch` (bad)

- **Compares:** each `schedule_khatians[]` entry `(survey_type, khatian_no)` of the proposed
  deed with the case khatian of the same survey (current or older), identifiers normalized.
- **Roles:** proposed deed, current khatian. One result per reference that has a khatian of
  the same survey in the case.
- **Pass:** deed BS 882, case BS khatian 882.
- **Fail:** deed BS 883, case BS khatian 882 → "দলিলে BS খতিয়ান নম্বর ৮৮৩, কিন্তু …-এ খতিয়ান নম্বর ৮৮২ …"
- **Ignored:** a reference to a survey with no khatian in the case (e.g. deed lists SA 214, the
  case has only the BS khatian) is not a finding. If no reference can be compared: skipped.
- **Known limits:** CITY and BS are different survey types here; a deed citing a CITY number
  against a BS khatian is not compared. With two khatians of the same survey, only the first
  (newest role) is used.

## `mouza_match` → `mouza_mismatch` (bad)

- **Compares:** `schedule_location.mouza` of the proposed deed with `location.mouza` of the
  current khatian: rapidfuzz ratio of `match_key` values ≥ `MOUZA_MIN` (90). If **both** print
  a JL number (`jl_no`), they must also be equal (normalized).
- **Roles:** proposed deed, current khatian. One result.
- **Pass:** চাঁদশী vs চাঁদশি (spelling), JL 45 vs 45.
- **Fail:** বাটাজোর vs চাঁদশী; or same mouza with JL 46 vs 45.
- **Skipped:** a mouza name could not be read on either side.
- **Known limits:** mouza names that are near-identical spellings of different places would
  pass on the name alone; the JL number is the stronger check when present.

## `seller_is_owner` → `seller_not_owner` (bad)

- **Compares:** every seller of the proposed deed with the owners of the **current khatian**,
  using `names_match` on `name_normalized`.
- **Roles:** proposed deed, current khatian. One result per seller.
- **Pass:** "মোঃ রহিম উদ্দীন" on the deed, "রহিম উদ্দিন" on the khatian.
- **Fail:** seller "জলিল" not among the owners → the message lists the khatian's owners.
- **Known limits:** findings.md says owners come "from the mutation if present, else from that
  khatian"; this version uses the current khatian only (as specified for this rule). In all
  scenarios the mutation and the khatian list the same owners; revisit when a mutation can be
  newer than the khatian. A seller who is an heir of a deceased owner not yet mutated is
  reported as not an owner (chain and heir rules give the context).

## `seller_father` → `seller_father_mismatch` (warn)

- **Compares:** for each seller who matched an owner, `father_or_husband_name` on the deed and
  on the khatian, with `normalize_name` then `names_match`.
- **Roles:** proposed deed, current khatian. One result per matched seller.
- **Same-name owners:** if several owners match the seller's name, the father's name chooses
  the one whose father matches. If none or more than one still fit, the result is
  `seller_father_mismatch` and the message says that owners with the same name exist.
- **Pass:** deed father রহমান, khatian father রহমান.
- **Fail (warn):** deed father কাশেম, khatian father রহমান.
- **Skipped:** the deed or the matched khatian owner has no father/husband name.
- **Known limits:** the relation marker (পিতা vs স্বামী) is not compared; a husband's name on one
  document and a father's name on the other gives a warning.

## `title_documents` → `document_missing` (warn)

- **Compares:** the proposed deed's `title_source_text` with the documents in the case.
- **Roles:** proposed deed.
- **Fail (warn):** the title contains ওয়ারিশ (inheritance) and the case has no heir certificate
  → "… কিন্তু কেসে ওয়ারিশ সনদ নেই। ওয়ারিশ সনদ-এর কপি যোগ করুন।", citing the title text.
- **Pass:** an heir certificate is present, or the title is by purchase (ক্রয়) or anything else.
- **Skipped:** no proposed deed, or the title could not be read.
- **Known limits:** only the word ওয়ারিশ is recognised; other inheritance wordings (e.g.
  উত্তরাধিকার) and other title sources (gift, partition) do not yet require a document.

## Seller resolution (`rules/common.py`)

`resolve_sellers(case)` matches every seller of the proposed deed to owners of the current
khatian with `names_match`. If several owners share the name, the father's/husband's name picks
one (`name_and_father`); if that still leaves none or several, the seller has **no matched
owner** (`ambiguous_same_name`). The identity rules and `sold_within_share` use the same result.

## `shares_add_up` → `area_sum_mismatch` (warn)

- **Compares:** for every khatian (current and older) and every mutation in the case, the
  owners' `share_fraction` sum with 1. Allowed difference `SHARE_TOLERANCE` = 0.001, because
  shares are printed in thousandths (".৩৩৪ + .৩৩৩ + .৩৩৩" = 1.000 passes).
- **Fallback:** if no owner prints a share, the sum of owners' `share_shatangsho` is compared
  with `total_area_shatangsho` (same relative tolerance).
- **One result per document.** Pass: .৪০০ + .৪০০ + .২০০. Fail: .৪০০ + .৪০০ + .১০০ (sum ০.৯).
- **Skipped:** a printed share could not be parsed (e.g. "।০ আনা"; `units` reports the unit),
  or neither shares nor areas are available.
- **Known limits:** a share printed per plot (not per khatian) is not supported (Decision 3).

## `sold_within_share` → `area_exceeds_share` (bad)

- **Compares:** the area the proposed deed transfers with what the sellers own on the current
  khatian. Exact `Decimal` comparison, no rounding: sold > available → bad; ≤ → pass.
- **Owner area in a plot = share_fraction × plot area** (`area_shatangsho`), summed over the
  matched sellers (findings.md, Decision 3; **needs expert check**).
- **Methods** (in `values.method`):
  - `per_dag`: every schedule dag is on the current khatian and each schedule plot has an
    area → one result per dag: sellers' area in that dag vs the deed's area for that dag.
  - `total_over_listed_dags`: dags all on the khatian but the deed gives only a total → the
    total vs the sellers' area summed over the listed dags.
  - `whole_khatian` (fallback): a schedule dag is **not** on the current khatian (or none was
    read) → `transferred_area_shatangsho` vs the sellers' `share_shatangsho` on the whole
    khatian. dag_mismatch reports the dag itself.
- **Example (demo):** রহিম owns .৪০০ of dag ৩০৫ (15 শতাংশ) = 6 শতাংশ; the deed transfers 10 →
  "খতিয়ানে দাগ ৩০৫-এ রহিম উদ্দিন-এর অংশ ৬ শতাংশ, কিন্তু দলিলে ১০ শতাংশ হস্তান্তর করা হচ্ছে …".
  Several sellers are named together with their combined share (মোট অংশ).
- **Skipped** (with a Bangla reason): a seller has no matched owner (`seller_not_owner` /
  `seller_father_mismatch` explain why), the transferred area or a seller's share could not be
  parsed (e.g. "২ কাঠা"; `units` reports it), or a compared plot has no area.
- **Sources:** the khatian owners' `share_text`, the plot `area_text` used, and the deed's area
  text (`schedule_plots[].area_text` or `transferred_area_text`).
- **Known limits:** a sale of an owner's share in a plot that is shared with another khatian
  (`khatian_share_fraction` < 1) uses the plot's khatian-share area (`area_shatangsho`), which is
  correct only if the owner's share applies to the khatian's part of the plot. Earlier sales by
  the same seller are not subtracted (needs the chain of deeds).

## `units` → `unsupported_unit` / `missing_unit` (warn)

- **Compares:** every area or share field in every document whose printed text exists but whose
  derived value is empty (`*_shatangsho`, `*_fraction`). `parse_area` (with `area_unit_text` as
  the hint on khatians and mutations) or `parse_share` tells why.
- **One finding per document and code**, listing the affected fields and the printed text.
  `unparseable_number` problems are not reported here (they are not unit problems).
- **Pass:** every printed area and share has a value. Fail: "২ কাঠা" → `unsupported_unit`;
  ".১৫০০" with no unit in the cell and no column header → `missing_unit`.
- **Known limits:** units are recognised by keyword (normalize.py); a unit misspelled by OCR is
  reported as missing.

## Sale vs share helper (`rules/area.py`)

`compute_sale_vs_share(case)` is the pure calculation behind `sold_within_share`, reused by
`co_owner_consent`. It returns a `SaleCheck`: `method` (`per_dag`, `total_over_listed_dags`,
`whole_khatian`, or None with a Bangla `skip_reason`), one `SalePart` per comparison (dags,
available, sold, sources), the matched sellers, and `shortfall` = sold − available where
positive.

## `co_owner_consent` → `heir_consent_missing` (warn)

- **Fires only if** the sale is compared dag by dag (`per_dag` or `total_over_listed_dags`, i.e.
  the sold dags are on the current khatian) **and** the deed transfers more than the sellers own
  there (shortfall > 0).
- **Co-owners** = owners of the current khatian not matched to any deed seller. They count as
  **co-heirs** if they appear on the case's heir certificate (`names_match`), or, when there is
  no heir certificate, if the deed's `title_source_text` contains ওয়ারিশ.
- **Consent** counts as present only if the co-owner is a seller on the same deed.
- **Values:** shortfall, co-owners and their printed shares. **Sources:** the deed's sellers and
  the co-owners' entries on the heir certificate (or the deed's title text).
- **Example (demo):** রহিম owns 6 of dag ৩০৫ and sells 10 → "বাকি ৪ শতাংশ করিম উদ্দিন বা সালমা
  খাতুন-এর অংশ থেকে আসতে হবে। তাঁদের সম্মতি বা সই কোনো কাগজে নেই। …"
- **Pass:** the sale is within the sellers' share (e.g. all three heirs sell together).
- **Skipped:** the sale cannot be computed (`compute_sale_vs_share` skip reason), the sold dag is
  not on the current khatian (`whole_khatian`: it is unclear whose share the rest comes from),
  no other owner exists, or the co-owners are not shown to be co-heirs (e.g. title by purchase
  and no heir certificate).

## `heirs_in_mutation` → `heir_missing_from_mutation` (warn)

- **Compares:** every heir on the heir certificate with the owners of the mutation, or of the
  current khatian if the case has no mutation (`names_match`). One result per living heir.
- **Deceased heirs** (`is_deceased`) are not compared; every message names them ("মৃত হিসাবে
  চিহ্নিত, তাই বাদ: …").
- **Fail:** the heir certificate lists a wife (জমিলা খাতুন) who is not an owner in the mutation.
- **Skipped:** no heir certificate (engine), or neither a mutation nor a current khatian.

## `ownership_chain` → `chain_break` (bad)

- **Predecessor P:** the heir certificate's deceased if present, else the buyer of the newest
  prior deed; neither → skipped.
- **Source khatian:** the older khatian whose `khatian_no` equals the mutation's
  `old_khatian_no`; else the newest older khatian; none → skipped.
- **Link 1 (P → source):** break if P is not an owner of the source khatian **and** not the
  buyer of a prior deed newer than the source khatian's `record_date` (if either date is
  unknown, a purchase by P counts).
- **Link 2 (each prior deed):** every seller must be an owner of the source khatian or of an
  older one (by survey order CS < SA < RS < BS/CITY). A deed with no readable seller is skipped.
- **Pass:** "মালিকানার ধারা {earliest year} থেকে বর্তমান পর্যন্ত ভাঙেনি: CS → SA → বায়া দলিল →
  ওয়ারিশ সনদ → নামজারি → বর্তমান খতিয়ান" (the documents in order).
- **Fail:** names the khatian and the record that do not connect, with the khatian's owners
  and the person who should connect (e.g. the 1985 deed's seller আব্দুল করিম is not an owner of
  SA খতিয়ান ২১৪, owned by নূর মোহাম্মদ).

## Known limits (heirs and chain)

- **Consent:** only co-sellers on the same deed count as consent. A power of attorney
  (আমমোক্তারনামা), a separate consent document or a court order is not recognised yet.
- **Chain order:** uses the survey order and record/registration dates when present; documents
  without dates are assumed to be in survey order. Mutations and heir certificates are not yet
  checked against each other beyond `heirs_in_mutation`.
- **No inheritance shares** are computed (Decision 5); who inherits how much is not checked.
- `co_owner_consent`, `heirs_in_mutation` and `ownership_chain` all **need expert check**:
  `docs/legal-notes.md` is empty, so none of these rules relies on a legal fact beyond
  findings.md.
