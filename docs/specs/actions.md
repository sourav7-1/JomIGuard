# Next actions

**Status: DRAFT.** `backend/app/services/actions.py` turns an assessment into at most 6 next
actions for the buyer: one per finding code (filled with the finding's values), one for coverage
gaps, one for fields to check by hand, and two that are **always** added. Sorted by priority
(1 high … 3 low), then severity (bad before warn), duplicates removed; the two always-actions
are always kept. No action says the land is safe (forbidden-words test).

`who` says who acts or helps: `buyer`, `seller`, `amin`, `lawyer`, `land_office`.

## Per finding code

| code | priority | who | action (Bangla template) | why |
|---|---|---|---|---|
| `area_exceeds_share` | 1 | buyer | `{seller_names}-কে জিজ্ঞেস করুন বাকি {excess} শতাংশ জমি কোথা থেকে আসছে।` | The sale is larger than the seller's share; the seller must explain where the rest comes from. |
| `heir_consent_missing` | 1 | seller | `{co_owners}-এর লিখিত সম্মতি বা আমমোক্তারনামা নিন।` | The rest belongs to co-heirs who are not on the deed. *(legal step: to verify)* |
| `seller_not_owner` | 1 | seller | `{seller} কীভাবে জমির মালিক হলেন, সেই কাগজ (দলিল, নামজারি বা ওয়ারিশ সনদ) চেয়ে নিন।` | The seller is not on the record; the missing link must be shown on paper. |
| `dag_mismatch` | 1 | amin | `দলিলের দাগ {deed_dag} আর খতিয়ানের দাগ {khatian_dags} একই জমি কিনা, একজন আমিন দিয়ে নকশা মিলিয়ে দেখুন।` | A dag mismatch can be a typing error or a different plot; only the map settles it. |
| `khatian_mismatch` | 1 | land_office | `দলিলে লেখা {survey} খতিয়ান {deed_khatian_no}-এর সার্টিফায়েড কপি ভূমি অফিস থেকে তুলে মিলিয়ে নিন।` | The deed cites another khatian; its official copy shows what it covers. |
| `mouza_mismatch` | 1 | land_office | `জমিটি কোন মৌজার ({deed_mouza} না {khatian_mouza}), ভূমি অফিসে যাচাই করুন।` | Different mouza means possibly different land. |
| `chain_break` | 1 | lawyer | `{to_document}-এর আগের হস্তান্তরের কাগজ চেয়ে নিন এবং মালিকানার ধারা একজন আইনজীবীকে দেখান।` | A gap in the ownership chain needs the missing transfer document and a professional reading. |
| `seller_father_mismatch` | 2 | seller | `{seller}-এর পরিচয় (পিতা/স্বামীর নাম) কাগজ দিয়ে নিশ্চিত হোন।` | Same name, different father: possibly a different person. |
| `heir_missing_from_mutation` | 2 | land_office | `{heir}-এর নাম নামজারিতে কেন নেই, ভূমি অফিসে জেনে নিন।` | An heir may still have a claim if the mutation left them out. |
| `document_missing` | 2 | seller | `বিক্রেতার কাছ থেকে {missing_document}-এর কপি চেয়ে নিন।` | The deed relies on a document (e.g. heir certificate) the case does not have. |
| `area_sum_mismatch` | 2 | land_office | `{document}-এ মালিকদের অংশের যোগফল কেন মেলে না, ভূমি অফিসে জেনে নিন।` | Shares not adding up suggest a missing owner or an outdated record. |
| `unsupported_unit` | 2 | seller | `"{printed}"-এর পরিমাণ শতাংশে কত, তা বিক্রেতার কাছ থেকে লিখিতভাবে জেনে নিন।` | Local units (কাঠা, বিঘা …) vary; the app does not convert them. |
| `missing_unit` | 2 | buyer | `{document}-এর পরিষ্কার কপি upload করুন, যাতে জমির একক পড়া যায়।` | Without a unit the area cannot be compared. |

## Other actions

| id | priority | who | action | when |
|---|---|---|---|---|
| `upload_documents` | 2 | buyer | `এই কাগজটি upload করুন: {documents}।` | Coverage is incomplete and a document role would let a skipped check run. |
| `review_fields` | 2 | buyer | `এই তথ্যগুলো নিজে মিলিয়ে নিন: {fields}।` | A rule used an extraction field flagged low/medium confidence. |
| `amin_field_survey` | 3 | amin | `একজন আমিন দিয়ে মাঠে জমি মাপান ও দখল দেখুন।` | **Always.** Possession and the real boundary are not in the documents. |
| `check_mortgage_and_cases` | 3 | lawyer | `সাব-রেজিস্ট্রি অফিস ও আদালতে বন্ধক বা মামলা আছে কিনা খোঁজ নিন।` | **Always.** Mortgages and court cases are not in these documents. |

Actions that imply a legal step are listed in `docs/legal-notes.md` under "Actions to verify
with an expert".
