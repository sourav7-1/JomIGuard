import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import EscrowDeal, EscrowEvent, IdentityVerification, Land, User
from app.services.escrow.bank import get_bank
from app.services.land_case import load_land_case

DEMO_LAND_ID = uuid.uuid5(uuid.NAMESPACE_URL, "jomiguard-demo-00026")


def seed_escrow(db: Session):
    user = db.scalar(select(User).where(User.username == settings.admin_username))
    land = db.get(Land, DEMO_LAND_ID)
    if not user or not land:
        return None
    if (
        db.scalar(
            select(IdentityVerification.id).where(
                IdentityVerification.user_id == user.id,
                IdentityVerification.party == "buyer",
                IdentityVerification.provider_ref == "escrow-demo-buyer-00026",
            )
        )
        is None
    ):
        db.add(
            IdentityVerification(
                land_id=None,
                user_id=user.id,
                party="buyer",
                status="verified",
                name_bn_as_per_nid="ডেমো ক্রেতা",
                father_name_as_per_nid="ডেমো অভিভাবক",
                provider="mock",
                provider_ref="escrow-demo-buyer-00026",
                consent_at=datetime.now(UTC),
                consent_version="identity-demo-v1",
                verified_at=datetime.now(UTC),
            )
        )
    previous_deals = db.scalars(
        select(EscrowDeal).where(EscrowDeal.land_id == DEMO_LAND_ID, ~EscrowDeal.archived)
    ).all()
    for previous in previous_deals:
        previous.archived = True
    next_created_at = max(
        [
            datetime.now(UTC),
            *(previous.created_at + timedelta(microseconds=1) for previous in previous_deals),
        ]
    )
    case = load_land_case(db, DEMO_LAND_ID)
    sellers = [row.name for row in case.proposed_deed.data.sellers] if case.proposed_deed else []
    deal = EscrowDeal(
        id=uuid.uuid4(),
        land_id=DEMO_LAND_ID,
        buyer_user_id=user.id,
        seller_names=sellers,
        price_paisa=600_000_000,
        bayna_paisa=50_000_000,
        deadline=date.today() + timedelta(days=60),
        state="draft",
        buyer_agreed=False,
        seller_agreed=False,
        conditions_snapshot=[],
        archived=False,
        created_at=next_created_at,
    )
    db.add(deal)
    db.flush()
    get_bank(db).open_escrow(deal.id, deal.bayna_paisa, f"{deal.id}:open")
    db.add(
        EscrowEvent(
            deal_id=deal.id,
            event="created",
            from_state="draft",
            to_state="draft",
            actor="demo_reset",
            message_bn="ডেমো বায়না চুক্তির খসড়া তৈরি হয়েছে।",
        )
    )
    db.commit()
    return deal.id
