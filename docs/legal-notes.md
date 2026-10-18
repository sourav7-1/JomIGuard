## Actions to verify with an expert

- verify: certified copy of prior deed from the sub-registry office and comparison procedure

- verify: bayna-nama registration rules, refund terms, bank partner

These actions are shown to users (`docs/specs/actions.md`) but are **not yet verified** against
law or office practice. Confirm each with a lawyer or land-office expert before release.

- **Field survey by an amin** ("একজন আমিন দিয়ে মাঠে জমি মাপান ও দখল দেখুন"): always shown.
  Verify that an amin is the right professional and what the check should cover.
- **Mortgage and court-case search** ("সাব-রেজিস্ট্রি অফিস ও আদালতে বন্ধক বা মামলা আছে কিনা খোঁজ নিন"):
  always shown. Verify where and how a buyer can search for mortgages and cases.
- **Co-heirs' written consent or power of attorney (আমমোক্তারনামা)** for `heir_consent_missing`:
  verify whether consent, a power of attorney, or the co-heirs joining the deed is required, and
  what form it must take.
- **Certified khatian copy from the land office** for `khatian_mismatch`: verify the procedure.
- **Asking the land office about a missing heir or wrong share sum** (`heir_missing_from_mutation`,
  `area_sum_mismatch`): verify whether this needs an objection or correction case (e.g. a
  mutation correction) and the steps involved.
- **Tracing a broken ownership chain with a lawyer** (`chain_break`): verify which documents
  establish a missing transfer.
