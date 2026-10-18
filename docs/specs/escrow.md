# Bayna escrow

The application models a draft transaction only. `BANK_PROVIDER=mock` writes integer paisa entries
to a local ledger; it does not move real funds. A licensed bank/payment partner must be selected
before live use.

States: draft → agreed → funded → conditions_met → registered → released. Funded or
conditions_met deals can be refunded after deadline; draft or agreed deals can be cancelled.
Buyer and seller agreements are separately recorded. Seller agreement uses the seller's one-time
verification link. Every state event is append-only.

Conditions are recalculated from the latest land case, assessment and identity results: verified
buyer and every deed seller, no bad finding, no `heir_consent_missing`, and a deed number registered
by the deadline. They are read-only. Money is integer paisa. The draft PDF contains names and land
schedule only and requires lawyer review before registry.
