# Land-case scenarios (answer key)

Hand-designed cases for the rule engine. Each folder holds the case's documents (each a valid
`ExtractedDocument`, derived fields filled as normalize would) and `expected.json` with **every**
non-passing finding. Codes and severities: `docs/specs/findings.md`. Format is checked by
`tests/unit/test_scenarios_format.py`; the rule engine itself does not exist yet.

All names and numbers are synthetic. Base family: রহমান (father ইউসুফ আলী, died 2009), heirs রহিম উদ্দিন,
করিম উদ্দিন, সালমা খাতুন (6 / 6 / 3 শতাংশ); dag 305 (15 শতাংশ); BS খতিয়ান 882, SA 214; মৌজা চাঁদশী,
গৌরনদী, বরিশাল; buyer রফিক আহমেদ.

✱ = `needs_expert_check`: the expected answer rests on a legal or survey fact that an expert must confirm
(see `description_bn`).

| id | folder | title | expected findings | risk |
|---|---|---|---|---|
| 01 | `01_demo_area_exceeds` | ডেমো: রহিমের অংশ ৬ শতাংশ, দলিলে বিক্রি ১০ শতাংশ | `area_exceeds_share`, `heir_consent_missing` | high |
| 02 | `02_sells_within_share` | রহিম তার ৬ শতাংশ থেকে ৫ শতাংশ বিক্রি করছেন | — | low |
| 03 | `03_honorific_variation` | দলিলে "মোঃ রহিম উদ্দিন", খতিয়ানে "রহিম উদ্দিন" | — | low |
| 04 | `04_sells_exact_share` | রহিম ঠিক তার পুরো ৬ শতাংশ বিক্রি করছেন | — | low |
| 05 | `05_all_heirs_sell_all` | তিন ওয়ারিশ একসাথে পুরো ১৫ শতাংশ বিক্রি করছেন | — | low |
| 06 | `06_two_heirs_sell_jointly` | রহিম ও করিম একসাথে ১০ শতাংশ বিক্রি করছেন | — | low |
| 07 | `07_seller_not_owner` | বিক্রেতা জলিল খতিয়ানে মালিক নন | `seller_not_owner` | high |
| 08 | `08_dag_mismatch` | দলিলে দাগ ৩০৬, খতিয়ানে দাগ ৩০৫ | `dag_mismatch` | high |
| 09 | `09_khatian_mismatch` | দলিলে বি.এস. খতিয়ান ৮৮৩, আসল খতিয়ান ৮৮২ | `khatian_mismatch` | high |
| 10 | `10_mouza_mismatch` | দলিলে মৌজা বাটাজোর, খতিয়ানে মৌজা চাঁদশী | `mouza_mismatch` | high |
| 11 | `11_owner_shares_sum_900` | খতিয়ানে মালিকদের অংশের যোগফল .৯০০ | `area_sum_mismatch` | medium ✱ |
| 12 | `12_heir_missing_from_mutation` | ওয়ারিশ সনদে ৪ জন, নামজারিতে ৩ জন | `heir_missing_from_mutation` | medium ✱ |
| 13 | `13_chain_break_sa_owner` | ১৯৮৫ সালের দলিলের বিক্রেতা এস.এ. খতিয়ানের মালিক নন | `chain_break` | high ✱ |
| 14 | `14_heir_cert_missing` | দলিলে ওয়ারিশ সূত্রে মালিকানা, কিন্তু ওয়ারিশ সনদ নেই | `document_missing` | medium |
| 15 | `15_unsupported_unit_katha` | দলিলে জমির পরিমাণ "২ কাঠা" | `unsupported_unit` | medium |
| 16 | `16_missing_unit_khatian` | খতিয়ানে জমির পরিমাণের একক নেই | `missing_unit` | medium |
| 17 | `17_multi_dag_within_share` | তিন দাগের খতিয়ান, দাগ ৩০৫ থেকে অংশের মধ্যে বিক্রি | — | low ✱ |
| 18 | `18_dag_and_area_mismatch` | দলিলে দাগ ৩০৬ এবং অংশের চেয়ে বেশি বিক্রি | `dag_mismatch`, `area_exceeds_share`, `heir_consent_missing` | high |
| 19 | `19_full_chain_cs_sa_bs` | সি.এস. থেকে বি.এস. পর্যন্ত পুরো মালিকানার ধারা মিলেছে | — | low ✱ |
| 20 | `20_seller_father_mismatch` | বিক্রেতার নাম মিলেছে, কিন্তু পিতার নাম ভিন্ন | `seller_father_mismatch` | medium |
