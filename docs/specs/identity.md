# Identity verification

**Status: DRAFT.** No code yet. Placement: after login (Day 39), together with Phase 6 (escrow).

## Purpose

1. **Seller is the owner (main value).** Verify that the person selling is the person named as
   owner on the khatian. Today the rules only compare *names printed on documents*; nothing
   proves who the person in front of the buyer is.
2. **KYC before escrow.** Know both buyer and seller before the partner bank moves any bayna
   money (`feature 3: Bayna escrow`).

## Approach

- Identity checks go through a **licensed e-KYC provider or the escrow partner bank**. The
  provider does the NID check and the face / liveness check.
- JomiGuard **never builds its own** face matching, liveness detection or NID database lookup,
  and never sees the raw identity data those checks use.
- JomiGuard receives only a **result** (below) and uses it in rules and in escrow.

## Provider interface

```text
start_verification(user, purpose) -> session
    purpose: "seller_ownership" | "escrow_kyc"
    session: {session_id, redirect_url or sdk_token, expires_at}

get_result(session) -> {
    status: "verified" | "failed" | "pending",
    name_bn_as_per_nid: str | None,
    father_name_as_per_nid: str | None,
    verified_at: datetime | None,
    provider: str,          # e.g. "mock", "<provider name>"
    provider_ref: str,      # the provider's reference for audits and disputes
}
```

- One implementation per provider behind this interface (`services/identity/`), chosen by a
  setting, like the extractor.
- A **mock provider** for development and demos: returns `verified` with a configured synthetic
  name, `failed`, or `pending`, without any real identity data.
- Polling or a provider webhook updates `pending` results; a session expires if not completed.

## Seller who is not a JomiGuard user

The seller may not have an account. The buyer starts the seller's check from the case:

1. The buyer creates a **verification link** for a seller on the case (one link per seller,
   purpose `seller_ownership`, tied to that case; it expires).
2. The buyer sends the link to the seller (the app shows it to copy or share; JomiGuard does not
   store the seller's phone number).
3. The seller opens the link, sees the same **consent screen in Bangla**, agrees, and verifies
   with the provider through that link. No account is needed for this.
4. The result is stored for that seller on that case (the result fields only) and the buyer
   sees `verified`, `failed` or `pending`.

If the seller does not verify (no result, or the link expired), the case shows
`seller_identity_unverified` (warn). A `failed` result also leaves the seller unverified.

## Data we store

| stored | never stored |
|---|---|
| `status`, `name_bn_as_per_nid`, `father_name_as_per_nid`, `verified_at`, `provider`, `provider_ref`, the purpose, the user, the time of consent | NID number, NID images (front/back), selfies or video, face templates or embeddings, signatures, date of birth, address, phone number, birth registration number |

If a provider sends more than the result fields, the extra data is dropped before anything is
saved or logged.

## Consent

- Before any verification, an explicit **consent screen in Bangla** states:
  - **what** is checked (জাতীয় পরিচয়পত্র ও চেহারা মিলিয়ে দেখা),
  - **by whom** (the named provider or bank, not JomiGuard),
  - **why** (seller is the khatian owner; KYC before escrow),
  - **what JomiGuard keeps** (only the result fields above),
  - that the user can **delete their data** at any time (except what the law requires the bank
    to keep).
- Verification starts only after the user agrees; the consent (text version, time, user) is
  recorded. Withdrawing consent deletes the stored result.

## Rules (later)

Both compare `name_bn_as_per_nid` with the matched owner on the current khatian using
`names_match` (`rules/names.py`) and are added to `findings.md` when built:

| code | severity | fires when |
|---|---|---|
| `seller_identity_unverified` | warn | A deed seller has no `verified` result for `seller_ownership` (not started, link not used or expired, pending, or failed). |
| `seller_nid_name_mismatch` | bad | A seller is verified, but `name_bn_as_per_nid` (and, if both exist, `father_name_as_per_nid` vs the owner's `father_or_husband_name`) does not match the khatian owner. |

Messages follow the usual rules: say what matched and what to do next; never call land safe.

## Escrow

Funds can move (deposit release or refund) **only when both buyer and seller are verified** for
`escrow_kyc`. The escrow module checks this before calling the partner bank; the bank's own
KYC still applies.

## Open questions for a lawyer

- Which data protection law applies, and what it requires for identity results and consent.
- Whether e-KYC for this use (land sale, escrow) is allowed with the chosen provider, and under
  which regulator's rules.
- The exact Bangla consent wording.
- How long verification results may or must be kept (retention period), and how deletion
  interacts with escrow records the bank must keep.
