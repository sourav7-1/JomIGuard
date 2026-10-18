import uuid
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select

from app.models import EscrowDeal, IdentityVerification, Land
from app.models.escrow import BankMockLedger
from app.services.escrow.bank import MockBank
from app.services.escrow.conditions import escrow_conditions
from app.services.escrow.state_machine import TRANSITIONS, transition


def test_every_allowed_transition_and_rejects_other_edges():
    for (state, event), target in TRANSITIONS.items():
        assert transition(state, event) == target
    for state in {s for s, _ in TRANSITIONS} | {"released", "refunded", "cancelled"}:
        for event in {e for _, e in TRANSITIONS}:
            if (state, event) not in TRANSITIONS:
                with pytest.raises(ValueError):
                    transition(state, event)
    state = "draft"
    for event in (
        "buyer_agrees",
        "deposit_confirmed",
        "conditions_checked",
        "registration_recorded",
        "release_confirmed",
    ):
        if event == "buyer_agrees":
            state = "agreed"
        else:
            state = transition(state, event)
    assert state == "released"


def test_conditions_are_derived_from_identity_findings_and_registered_deed():
    seller = SimpleNamespace(name="à¦¸à§‡à¦²à¦¾à¦°")
    case = SimpleNamespace(
        proposed_deed=SimpleNamespace(data=SimpleNamespace(sellers=[seller])),
        identity=[SimpleNamespace(status="verified", seller_name_on_deed="à¦¸à§‡à¦²à¦¾à¦°")],
    )
    buyer = SimpleNamespace(status="verified")
    finding = SimpleNamespace(status="warn", code="seller_identity_unverified")
    assessment = SimpleNamespace(findings=[finding])
    rows = escrow_conditions(
        case, assessment, buyer, date.today() + timedelta(days=1), ("D-1", date.today())
    )
    assert [r["met"] for r in rows] == [True, True, True, True]
    assessment.findings = [SimpleNamespace(status="bad", code="bad")]
    rows = escrow_conditions(case, assessment, buyer, date.today() + timedelta(days=1), None)
    assert [r["met"] for r in rows] == [True, False, True, False]
    assessment.findings = [SimpleNamespace(status="warn", code="heir_consent_missing")]
    rows = escrow_conditions(case, assessment, buyer, date.today() + timedelta(days=1), None)
    assert rows[2]["met"] is False


def test_mock_bank_idempotency_stores_paisa_integer_once():
    db = MagicMock()
    db.scalar.side_effect = [None, object()]
    bank = MockBank(db)
    bank.deposit("deal-id", 2050, "deal-id:deposit")
    bank.deposit("deal-id", 2050, "deal-id:deposit")
    assert db.add.call_count == 1
    assert db.add.call_args.args[0].amount_paisa == 2050
    assert type(db.add.call_args.args[0].amount_paisa) is int


def test_escrow_create_deposit_and_deadline_refund(client):
    from conftest import TEST_ADMIN_ID, TestSession

    with TestSession() as db:
        land = Land(
            owner_id=TEST_ADMIN_ID, district="", upazila="", mouza="demo", dag_no="1", khatian_no=""
        )
        db.add(land)
        db.commit()
        land_id = land.id
    response = client.post(
        f"/lands/{land_id}/escrow",
        json={
            "price": "100.00",
            "bayna": "20.50",
            "deadline": (date.today() + timedelta(days=1)).isoformat(),
        },
    )
    assert response.status_code == 201
    deal_id = response.json()["id"]
    assert response.json()["price_paisa"] == 10000
    assert isinstance(response.json()["price_paisa"], int)
    client.post(f"/escrow/{deal_id}/agree")
    # This land has no seller; make both explicit agreement flags through the isolated setup.
    with TestSession() as db:
        deal = db.get(EscrowDeal, deal_id)
        deal.seller_agreed = True
        deal.state = "agreed"
        db.commit()
    first = client.post(f"/escrow/{deal_id}/deposit", headers={"Idempotency-Key": "same-deposit"})
    second = client.post(f"/escrow/{deal_id}/deposit", headers={"Idempotency-Key": "same-deposit"})
    assert first.status_code == second.status_code == 200
    assert first.json()["balances"] == second.json()["balances"]
    assert client.post(f"/escrow/{deal_id}/release").status_code == 409
    expired = client.post(f"/escrow/{deal_id}/demo/expire")
    assert expired.status_code == 200
    assert expired.json()["balances"]["buyer_paisa"] == 2050
    with TestSession() as db:
        rows = db.scalars(select(BankMockLedger).where(BankMockLedger.deal_id == deal_id)).all()
        assert sum(r.operation == "deposit" for r in rows) == 1
        assert sum(r.operation == "refund" for r in rows) == 1
        assert all(type(r.amount_paisa) is int for r in rows)


def test_seller_acceptance_requires_associated_link(client):
    import hashlib
    import uuid
    from datetime import UTC, datetime

    from conftest import TEST_ADMIN_ID, TestSession

    from app.models.identity import SellerLink

    with TestSession() as db:
        land = Land(
            owner_id=TEST_ADMIN_ID, district="", upazila="", mouza="demo", dag_no="1", khatian_no=""
        )
        db.add(land)
        db.commit()
        land_id = land.id
    created = client.post(
        f"/lands/{land_id}/escrow",
        json={
            "price": "100",
            "bayna": "20",
            "deadline": (date.today() + timedelta(days=1)).isoformat(),
        },
    ).json()
    token = "synthetic-seller-consent"
    with TestSession() as db:
        db.add(
            SellerLink(
                land_id=land_id,
                seller_name_on_deed="Synthetic Seller",
                token_hash=hashlib.sha256(token.encode()).hexdigest(),
                expires_at=datetime.now(UTC) + timedelta(days=1),
                escrow_deal_id=uuid.UUID(created["id"]),
                used_at=datetime.now(UTC),
            )
        )
        db.add(
            IdentityVerification(
                land_id=land_id,
                user_id=None,
                party="seller",
                seller_name_on_deed="Synthetic Seller",
                status="verified",
                name_bn_as_per_nid="Synthetic Seller",
                father_name_as_per_nid="Synthetic",
                provider="mock",
                provider_ref="synthetic-ref",
                consent_at=datetime.now(UTC),
                consent_version="test",
                verified_at=datetime.now(UTC),
            )
        )
        db.commit()
    result = client.post(f"/verify/{token}/escrow-agree")
    assert result.status_code == 200
    assert result.json() == {"accepted": True}
    with TestSession() as db:
        deal = db.get(EscrowDeal, created["id"])
        assert deal.seller_agreed is True and deal.state == "draft"


def test_demo_reset_archives_old_deal_and_creates_fresh_demo_draft(client):
    from datetime import date

    from conftest import TEST_ADMIN_ID, TestSession

    from app.models import EscrowDeal, EscrowEvent
    from app.models.escrow import BankMockLedger
    from app.scripts.escrow_seed import DEMO_LAND_ID, seed_escrow

    with TestSession() as db:
        db.add(
            Land(
                id=DEMO_LAND_ID,
                owner_id=TEST_ADMIN_ID,
                district="",
                upazila="",
                mouza="নমুনা",
                dag_no="1",
                khatian_no="",
            )
        )
        db.flush()
        old_id = uuid.uuid4()
        db.add(
            EscrowDeal(
                id=old_id,
                land_id=DEMO_LAND_ID,
                buyer_user_id=TEST_ADMIN_ID,
                seller_names=[],
                price_paisa=1,
                bayna_paisa=1,
                deadline=date.today(),
                state="funded",
                buyer_agreed=True,
                seller_agreed=True,
                conditions_snapshot=[],
            )
        )
        db.flush()
        db.add(
            BankMockLedger(
                deal_id=old_id,
                idempotency_key=f"{old_id}:old",
                operation="deposit",
                amount_paisa=1,
            )
        )
        db.add(
            EscrowEvent(
                deal_id=old_id,
                event="deposit_confirmed",
                from_state="agreed",
                to_state="funded",
                actor="test",
                message_bn="নমুনা",
            )
        )
        db.commit()
        first_id = seed_escrow(db)
        assert first_id != old_id
        old = db.get(EscrowDeal, old_id)
        assert old.archived and old.state == "funded" and old.buyer_agreed and old.seller_agreed
        assert old.bayna_paisa == 1 and old.deadline == date.today()
        assert db.query(EscrowEvent).filter_by(deal_id=old_id).count() == 1
        ledger = db.query(BankMockLedger).filter_by(deal_id=old_id).all()
        assert len(ledger) == 1 and ledger[0].operation == "deposit"
        first = db.get(EscrowDeal, first_id)
        assert first.state == "draft" and not first.archived
        assert not first.buyer_agreed and not first.seller_agreed
        assert first.deadline > date.today()
        assert db.query(EscrowEvent).filter_by(deal_id=first_id).count() == 1
        second_id = seed_escrow(db)
        assert second_id != first_id
        assert db.get(EscrowDeal, first_id).archived
        current = client.get("/demo/escrow/00026")
        assert current.status_code == 200 and current.json()["id"] == str(second_id)
        assert current.json()["state"] == "draft"
        assert client.get(f"/escrow/{first_id}").status_code == 404
