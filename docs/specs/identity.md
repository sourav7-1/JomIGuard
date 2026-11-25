# Identity verification

**Status:** mock provider and NID name reading implemented (`services/identity/`, `api/identity.py`).
The provider check of NID genuineness and face match is still a mock.

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
  and never sees the raw identity data those checks use, except the **name fields of the NID
  photo** (below).
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

## NID name reading (owner decision, 2026-11-26)

The owner allows reading **only the name fields** of an NID photo, to match the seller or buyer
with the khatian and the deed. Everything else on the card stays forbidden.

- **What is read:** `name_bn`, `name_en`, `father_or_husband_name` (fields.md, `nid`). The prompt
  forbids the NID number, date of birth, address, blood group, mother's name, signature and photo;
  `NidNames` keeps only the three fields, so anything else a model returns is dropped before it can
  be stored, returned or logged.
- **Endpoints:** `POST /verify/{token}/nid` (seller, after consent) and `POST /me/verification/nid`
  (buyer, `consent=true`). Multipart `image` (max 5 MB) plus the mocked provider `outcome`.
- **The image stays in memory.** It is read in the request and dropped: never written to MinIO,
  disk or the extraction cache.
- **Chain:** a paid Anthropic model (only when `ANTHROPIC_API_KEY` and the LLM settings are set),
  then local Tesseract, which keeps only the "নাম", "Name", "পিতা"/"স্বামী" lines. **Never Gemini**:
  its free tier may use inputs for training. A Tesseract read is stored as `name_source = "ocr"`.
- **Matching** (`nid_match` in `rules/names.py`, on top of `names_match`: honorifics removed,
  spelling variants, father/husband name when both are present):

  | result | Bangla | seller: when | buyer: when |
  |---|---|---|---|
  | `matched` | মিলেছে | the name matches the deed seller and a matched khatian owner, father/husband not different | the name matches a buyer on the proposed deed of one of the user's own cases, father/husband not different |
  | `partial` | আংশিক | only one of the two, or the father/husband name differs | the father/husband name differs |
  | `no_match` | মেলেনি | neither | no buyer |
  | `unreadable` | পড়া যায়নি | no name could be read; the link is **not** used up, so the seller can try again or type the name | same |

  A buyer with no proposed deed in their cases gets no match result (`null`); there is no buyer
  rule, the result card only.
- **Rule:** `seller_identity` recomputes the result on the current documents: `matched` passes,
  `partial` gives `seller_nid_name_partial` (warn), `no_match` gives `seller_nid_name_mismatch`
  (bad). An OCR-read name never gives a mismatch: it goes to "যাচাই করা যায়নি / মিলিয়ে নিন"
  (rules.md, OCR guard).
- **What it does not prove:** a name match does not prove the NID is genuine; that needs the
  Election Commission service through a provider (mocked in this demo). The UI says so.
- **Audit:** one log line `identity.nid_read party=… result=… source=… status=… land=…`, with no
  names and no image data.
- **Tests** use only synthetic cards from `ml/synth/nid.py` (watermarked "নমুনা / SAMPLE",
  placeholder ID number and birth date).

## Data we store

| stored | never stored |
|---|---|
| `status`, `name_bn_as_per_nid`, `name_en_as_per_nid`, `father_name_as_per_nid`, `match_result`, `match_confidence`, `name_source` (ai / ocr / typed), `verified_at`, `provider`, `provider_ref`, the party, the user, the time and version of consent | NID number, NID images (front/back), selfies or video, face templates or embeddings, signatures, date of birth, address, blood group, mother's name, phone number, birth registration number |

If a provider sends more than the result fields, the extra data is dropped before anything is
saved or logged.

## Consent

- Before any verification, an explicit **consent screen in Bangla** states:
  - **what** is checked (জাতীয় পরিচয়পত্র ও চেহারা মিলিয়ে দেখা),
  - **by whom** (the named provider or bank, not JomiGuard),
  - **why** (seller is the khatian owner; KYC before escrow),
  - **what JomiGuard keeps** (only the result fields above), and the line
    "শুধু নাম মেলাতে ছবি পড়া হবে; নম্বর, জন্মতারিখ বা ছবি রাখা হবে না" before the NID photo;
    consent version `identity-nid-name-v1`,
  - that the user can **delete their data** at any time (except what the law requires the bank
    to keep).
- Verification starts only after the user agrees; the consent (text version, time, user) is
  recorded. Withdrawing consent deletes the stored result.

## Rules

`seller_identity` (findings.md) compares `name_bn_as_per_nid` with the deed seller and the
matched owner on the current khatian using `nid_match` (`rules/names.py`):

| code | severity | fires when |
|---|---|---|
| `seller_identity_unverified` | warn | A deed seller has no `verified` result for `seller_ownership` (not started, link not used or expired, pending, failed, or the NID was unreadable). |
| `seller_nid_name_partial` | warn | The name matches only the deed seller or only the owner, or the father/husband name differs. |
| `seller_nid_name_mismatch` | bad | The name matches neither the deed seller nor the owner. |

Both name codes go to `to_verify` instead when the name was read by OCR.

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
