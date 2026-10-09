# Finding vocabulary

**Status: DRAFT.** The rule engine reports only *non-passing* checks as findings. This file is the
answer key's vocabulary: `backend/tests/scenarios/*/expected.json` may only use codes listed here,
with the severity listed here (checked by `backend/tests/unit/test_scenarios_format.py`).

## Severity

| severity | meaning |
|---|---|
| `bad` | Major mismatch between documents. |
| `warn` | Something needs checking; the documents alone cannot settle it. |

Passing checks are not listed.

## Risk

| risk | rule |
|---|---|
| `high` | at least one `bad` finding |
| `medium` | no `bad`, at least one `warn` |
| `low` | no findings |

A `low` risk only means the documents in the case agree with each other. The app never calls land
safe (CLAUDE.md): disputes, possession and mortgages do not show up in these documents.

## Codes

| code | group | severity | meaning (English) | অর্থ (বাংলা) |
|---|---|---|---|---|
| `dag_mismatch` | identity | bad | The deed's dag number is not on the khatian. | দলিলের দাগ নম্বর খতিয়ানে নেই। |
| `khatian_mismatch` | identity | bad | The deed's khatian number differs from the khatian of the same survey. | দলিলের খতিয়ান নম্বর একই জরিপের খতিয়ানের সাথে মেলে না। |
| `mouza_mismatch` | identity | bad | The deed's mouza differs from the khatian's mouza. | দলিলের মৌজা খতিয়ানের মৌজার সাথে মেলে না। |
| `seller_not_owner` | identity | bad | A seller on the deed is not an owner on the khatian or mutation. | দলিলের বিক্রেতা খতিয়ান বা নামজারিতে মালিক হিসাবে নেই। |
| `seller_father_mismatch` | identity | warn | The seller's name matches an owner, but the father's/husband's name differs. | বিক্রেতার নাম মিলেছে, কিন্তু পিতা/স্বামীর নাম মেলে না। |
| `area_exceeds_share` | area | bad | The deed transfers more land than the sellers own. | দলিলে বিক্রেতার অংশের চেয়ে বেশি জমি হস্তান্তর হচ্ছে। |
| `area_sum_mismatch` | area | warn | Owner shares on a khatian or mutation do not add up to the whole. | খতিয়ান বা নামজারিতে মালিকদের অংশের যোগফল পুরো জমির সমান নয়। |
| `unsupported_unit` | area | warn | An area is in a unit the app does not convert (বিঘা, কাঠা, আনা …). | জমির পরিমাণ এমন এককে লেখা যা app রূপান্তর করে না (বিঘা, কাঠা, আনা …)। |
| `missing_unit` | area | warn | An area has no readable unit, in the cell or the column header. | জমির পরিমাণের কোনো একক পড়া যায়নি, ঘরে বা কলামের শিরোনামে। |
| `heir_consent_missing` | heirs | warn | A seller sells beyond their own share and the other co-owners are not on the deed. | বিক্রেতা নিজের অংশের বেশি বিক্রি করছেন, অথচ অন্য অংশীদাররা দলিলে নেই। |
| `heir_missing_from_mutation` | heirs | warn | An heir on the heir certificate is not an owner in the mutation. | ওয়ারিশ সনদের একজন ওয়ারিশ নামজারিতে মালিক হিসাবে নেই। |
| `chain_break` | chain | bad | Ownership does not connect from one record to the next. | এক রেকর্ড থেকে পরের রেকর্ডে মালিকানার ধারা মেলে না। |
| `document_missing` | completeness | warn | A document the case relies on is not in the case. | কেসের কাগজ যে কাগজের ওপর নির্ভর করে, সেটা কেসে নেই। |

## When each check fires (MVP)

General rules:

- A check runs only when the documents it compares are present and the values it needs are
  filled. A missing value is **not** a finding by itself; units are covered by `missing_unit`
  and `unsupported_unit`, and documents by `document_missing`.
- People are matched on `name_normalized`. **Spelling or honorific differences (মোঃ, মোছাঃ, শেখ)
  are not a finding.**
- "Khatian" below means the case's most recent khatian (BS, else RS, SA, CS) unless a rule says
  otherwise. Owners are taken from the mutation if present, else from that khatian.

| code | fires when |
|---|---|
| `dag_mismatch` | A deed's `schedule_plots[].dag_no` is not among the khatian's `plots[].dag_no`. Compared only against a khatian of the same survey as one of the deed's `schedule_khatians`, because dag numbers can change between surveys. |
| `khatian_mismatch` | The deed lists a khatian for a survey type that is in the case, and no `schedule_khatians` entry with that survey type has that khatian's `khatian_no`. |
| `mouza_mismatch` | `schedule_location.mouza` ≠ the khatian's `location.mouza`. |
| `seller_not_owner` | A deed seller's `name_normalized` is not among the owners. |
| `seller_father_mismatch` | A seller matches an owner by name, but `father_or_husband_name` differs (after the same normalization as names). |
| `area_exceeds_share` | `transferred_area_shatangsho` > the sellers' combined share. Per seller: `share_fraction` × the sold dag's `area_shatangsho` if the dag is on the khatian (Decision 3, *needs expert check*), else the seller's `share_shatangsho`. Not evaluated if either side has no shatangsho value. |
| `area_sum_mismatch` | On a khatian or mutation, owners' `share_fraction` do not sum to 1, or owners' `share_shatangsho` do not sum to `total_area_shatangsho`. |
| `unsupported_unit` | normalize met a unit other than একর, শতাংশ or a decimal fraction (Decision 2). One finding per document. |
| `missing_unit` | normalize found no unit in `area_text` and no `area_unit_text` (Decision 8). One finding per document. |
| `heir_consent_missing` | `area_exceeds_share` fires and at least one other owner of the land is not a seller on that deed. The app does not decide what form consent must take; it asks the user to check. |
| `heir_missing_from_mutation` | A heir (not marked `is_deceased`) on the heir certificate is not an owner in the mutation. Not evaluated without both documents. |
| `chain_break` | Order the *history*: CS, SA, RS khatians, then registered deeds (registration year), heir certificates (date of death) and mutations (order date) by date, then BS. Between consecutive records present in the case: a deed's sellers are not owners of the record before it; a heir certificate's deceased is not an owner or buyer in the record before it; or a newer record has an owner who is not a previous owner, buyer or heir. The case's newest (e.g. draft) deed is not part of the history; its seller is checked by `seller_not_owner`. Missing heirs are `heir_missing_from_mutation`, not `chain_break`. |
| `document_missing` | A deed's `title_source_text` says the land was inherited (ওয়ারিশ) and the case has no heir certificate. More triggers will be added as specs grow. |

No rule computes inheritance shares. Shares come from the mutation / BS khatian (Decision 5 in
`fields.md`).
