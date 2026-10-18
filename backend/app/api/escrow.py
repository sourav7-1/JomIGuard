import html
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import authenticated_user
from app.core.config import settings
from app.db.session import get_db
from app.models import (
    BankMockLedger,
    EscrowDeal,
    EscrowEvent,
    IdentityVerification,
    Land,
    LandAssessment,
    User,
)
from app.models.identity import SellerLink
from app.schemas.assessment import Assessment
from app.services.escrow.bank import get_bank
from app.services.escrow.conditions import escrow_conditions
from app.services.escrow.state_machine import transition
from app.services.land_case import load_land_case
from app.services.report import render_report_pdf
from app.services.risk import assess
from app.services.rules import run_rules

router = APIRouter(tags=["escrow"])
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(authenticated_user)]


class DealIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    price: Decimal = Field(gt=0)
    bayna: Decimal = Field(gt=0)
    deadline: date


class RegistrationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    deed_no: str = Field(min_length=1, max_length=100)
    date: date


def _paisa(value: Decimal) -> int:
    try:
        paisa = value * 100
        if paisa != paisa.to_integral_value():
            raise ValueError("টাকার অঙ্ক পয়সায় সঠিকভাবে প্রকাশযোগ্য হতে হবে।")
        return int(paisa)
    except InvalidOperation:
        raise ValueError("টাকার অঙ্ক সঠিক নয়।") from None


def _owned(db, deal_id, user):
    deal = db.get(EscrowDeal, deal_id)
    if deal is None or deal.archived or deal.buyer_user_id != user.id:
        raise HTTPException(404, "চুক্তিটি পাওয়া যায়নি।")
    return deal


def _record(db, deal, event, actor, target=None):
    before = deal.state
    try:
        deal.state = target or transition(before, event)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None
    db.add(
        EscrowEvent(
            deal_id=deal.id,
            event=event,
            from_state=before,
            to_state=deal.state,
            actor=actor,
            message_bn="চুক্তির অবস্থা হালনাগাদ হয়েছে।",
        )
    )


def _assessment(db, land_id):
    row = db.scalar(
        select(LandAssessment)
        .where(LandAssessment.land_id == land_id)
        .order_by(LandAssessment.created_at.desc(), LandAssessment.id.desc())
        .limit(1)
    )
    if row:
        return Assessment(**row.result)
    case = load_land_case(db, land_id)
    return assess(case, run_rules(case))


def _conditions(db, deal):
    case = load_land_case(db, deal.land_id)
    buyer = db.scalar(
        select(IdentityVerification)
        .where(
            IdentityVerification.user_id == deal.buyer_user_id,
            IdentityVerification.party == "buyer",
        )
        .order_by(IdentityVerification.created_at.desc())
        .limit(1)
    )
    land = db.get(Land, deal.land_id)
    registered = next(
        (
            doc.data
            for doc in case.documents
            if doc.doc_type == "deed"
            and not doc.data.is_draft
            and doc.data.deed_no == deal.registration_deed_no
            and doc.data.registration_date is not None
            and doc.data.registration_date == deal.registration_date
            and doc.data.registration_date <= deal.deadline
            and any(plot.dag_no == land.dag_no for plot in doc.data.schedule_plots)
        ),
        None,
    )
    registration = (registered.deed_no, registered.registration_date) if registered else None
    assessment = _assessment(db, deal.land_id)
    result = escrow_conditions(case, assessment, buyer, deal.deadline, registration)
    deal.conditions_snapshot = result
    return result


def _out(db, deal):
    return {
        "id": str(deal.id),
        "land_id": str(deal.land_id),
        "state": deal.state,
        "price_paisa": deal.price_paisa,
        "bayna_paisa": deal.bayna_paisa,
        "deadline": deal.deadline.isoformat(),
        "buyer_agreed": deal.buyer_agreed,
        "seller_agreed": deal.seller_agreed,
        "conditions": deal.conditions_snapshot,
        "balances": get_bank(db).balances(deal.id),
        "events": [
            {
                "event": e.event,
                "from_state": e.from_state,
                "to_state": e.to_state,
                "actor": e.actor,
                "message_bn": e.message_bn,
                "created_at": e.created_at.isoformat(),
            }
            for e in db.scalars(
                select(EscrowEvent)
                .where(EscrowEvent.deal_id == deal.id)
                .order_by(EscrowEvent.created_at, EscrowEvent.id)
            ).all()
        ],
    }


@router.post("/lands/{land_id}/escrow", status_code=201)
def create_deal(land_id: uuid.UUID, body: DealIn, db: Db, user: CurrentUser):
    land = db.get(Land, land_id)
    if land is None or land.owner_id != user.id:
        raise HTTPException(404, "Land not found")
    if body.deadline <= date.today():
        raise HTTPException(422, "সময়সীমা ভবিষ্যতের তারিখ হতে হবে।")
    price, bayna = _paisa(body.price), _paisa(body.bayna)
    if bayna > price:
        raise HTTPException(422, "বায়নার অঙ্ক মোট দামের বেশি হতে পারবে না।")
    case = load_land_case(db, land_id)
    sellers = [s.name for s in case.proposed_deed.data.sellers] if case.proposed_deed else []
    deal = EscrowDeal(
        land_id=land_id,
        buyer_user_id=user.id,
        seller_names=sellers,
        price_paisa=price,
        bayna_paisa=bayna,
        deadline=body.deadline,
    )
    db.add(deal)
    db.flush()
    get_bank(db).open_escrow(deal.id, bayna, f"{deal.id}:open")
    db.add(
        EscrowEvent(
            deal_id=deal.id,
            event="created",
            from_state="draft",
            to_state="draft",
            actor=str(user.id),
            message_bn="খসড়া বায়না চুক্তি তৈরি হয়েছে।",
        )
    )
    db.commit()
    return _out(db, deal)


@router.get("/escrow/{deal_id}")
def get_deal(deal_id: uuid.UUID, db: Db, user: CurrentUser):
    deal = _owned(db, deal_id, user)
    if date.today() > deal.deadline and deal.state in {"funded", "conditions_met"}:
        bank = get_bank(db)
        bank.refund(deal.id, deal.bayna_paisa, f"{deal.id}:deadline-refund")
        _record(db, deal, "deadline_passed", "system")
        db.commit()
    _conditions(db, deal)
    db.commit()
    return _out(db, deal)


@router.get("/demo/escrow/{case_id}")
def get_demo_deal(case_id: str, db: Db, user: CurrentUser):
    if case_id != "00026":
        raise HTTPException(404, "Demo escrow not found")
    land_id = uuid.uuid5(uuid.NAMESPACE_URL, "jomiguard-demo-00026")
    land = db.get(Land, land_id)
    if land is None or land.owner_id != user.id:
        raise HTTPException(404, "Demo escrow not found")
    deal = db.scalar(
        select(EscrowDeal)
        .where(EscrowDeal.land_id == land_id, ~EscrowDeal.archived)
        .order_by(EscrowDeal.created_at.desc(), EscrowDeal.id.desc())
        .limit(1)
    )
    if deal is None:
        raise HTTPException(404, "Demo escrow not found")
    if date.today() > deal.deadline and deal.state in {"funded", "conditions_met"}:
        get_bank(db).refund(deal.id, deal.bayna_paisa, f"{deal.id}:deadline-refund")
        _record(db, deal, "deadline_passed", "system")
    _conditions(db, deal)
    db.commit()
    return _out(db, deal)


@router.post("/escrow/{deal_id}/agree")
def buyer_agree(deal_id: uuid.UUID, db: Db, user: CurrentUser):
    deal = _owned(db, deal_id, user)
    if deal.buyer_agreed:
        return _out(db, deal)
    if deal.seller_agreed:
        _record(db, deal, "buyer_agrees", str(user.id))
    else:
        db.add(
            EscrowEvent(
                deal_id=deal.id,
                event="buyer_agrees",
                from_state=deal.state,
                to_state=deal.state,
                actor=str(user.id),
                message_bn="ক্রেতা খসড়ায় সম্মতি দিয়েছেন।",
            )
        )
    deal.buyer_agreed = True
    if deal.seller_agreed:
        deal.state = "agreed"
    db.commit()
    return _out(db, deal)


@router.post("/verify/{token}/escrow-agree")
def seller_agree(token: str, db: Db):
    import hashlib

    token_hash = hashlib.sha256(token.encode()).hexdigest()
    link = db.scalar(select(SellerLink).where(SellerLink.token_hash == token_hash))
    now = datetime.now(link.expires_at.tzinfo) if link else datetime.now()
    if (
        link is None
        or link.used_at is None
        or link.expires_at <= now
        or link.escrow_deal_id is None
    ):
        raise HTTPException(
            410,
            (
                "\u09ac\u09bf\u0995\u09cd\u09b0\u09c7\u09a4\u09be\u09b0 link "
                "\u09ae\u09c7\u09df\u09be\u09a6\u09cb\u09a4\u09cd\u09a4\u09c0\u09b0\u09cd\u09a3"
            ),
        )
    verification = db.scalar(
        select(IdentityVerification)
        .where(
            IdentityVerification.land_id == link.land_id,
            IdentityVerification.party == "seller",
            IdentityVerification.seller_name_on_deed == link.seller_name_on_deed,
            IdentityVerification.status == "verified",
            IdentityVerification.created_at >= link.created_at,
        )
        .order_by(IdentityVerification.created_at.desc())
        .limit(1)
    )
    if verification is None:
        raise HTTPException(
            409,
            (
                "\u0986\u0997\u09c7 \u09ac\u09bf\u0995\u09cd\u09b0\u09c7\u09a4\u09be\u09b0 "
                "\u09aa\u09b0\u09bf\u099a\u09df \u09af\u09be\u099a\u09be\u0987 "
                "\u09b8\u09ae\u09cd\u09aa\u09a8\u09cd\u09a8 \u0995\u09b0\u09c1\u09a8"
            ),
        )
    deal = db.get(EscrowDeal, link.escrow_deal_id)
    if deal is None or deal.archived:
        raise HTTPException(
            410,
            (
                "\u098f\u0987 link \u09a6\u09bf\u09df\u09c7 "
                "\u099a\u09c1\u0995\u09cd\u09a4\u09bf \u0996\u09c1\u09b2\u09c7 \u09a8\u09be"
            ),
        )
    if deal.seller_agreed:
        return {"accepted": True}
    if deal.buyer_agreed:
        _record(db, deal, "seller_agrees", link.seller_name_on_deed)
    else:
        db.add(
            EscrowEvent(
                deal_id=deal.id,
                event="seller_agrees",
                from_state=deal.state,
                to_state=deal.state,
                actor=link.seller_name_on_deed,
                message_bn=(
                    "\u09ac\u09bf\u0995\u09cd\u09b0\u09c7\u09a4\u09be "
                    "\u0996\u09b8\u09a1\u09bc\u09be\u09df "
                    "\u09b8\u09ae\u09cd\u09ae\u09a4\u09bf "
                    "\u09a6\u09bf\u09df\u09c7\u099b\u09c7\u09a8"
                ),
            )
        )
    deal.seller_agreed = True
    if deal.buyer_agreed:
        deal.state = "agreed"
    db.commit()
    return {"accepted": True}


@router.post("/escrow/{deal_id}/deposit")
def deposit(
    deal_id: uuid.UUID,
    db: Db,
    user: CurrentUser,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    deal = _owned(db, deal_id, user)
    bank_key = f"{deal.id}:{idempotency_key or 'deposit'}"
    existing = db.scalar(select(BankMockLedger).where(BankMockLedger.idempotency_key == bank_key))
    if existing is not None:
        if (
            existing.deal_id != deal.id
            or existing.operation != "deposit"
            or existing.amount_paisa != deal.bayna_paisa
        ):
            raise HTTPException(409, "Idempotency key conflicts with an existing transaction.")
        return _out(db, deal)
    if deal.state != "agreed" or not deal.buyer_agreed or not deal.seller_agreed:
        raise HTTPException(409, "দুই পক্ষের সম্মতির পর টাকা জমা দেওয়া যাবে।")
    get_bank(db).deposit(deal.id, deal.bayna_paisa, bank_key)
    _record(db, deal, "deposit_confirmed", str(user.id))
    db.commit()
    return _out(db, deal)


@router.post("/escrow/{deal_id}/check")
def check_conditions(deal_id: uuid.UUID, db: Db, user: CurrentUser):
    deal = _owned(db, deal_id, user)
    if deal.state not in {"funded", "conditions_met"}:
        raise HTTPException(409, "টাকা জমার পর শর্ত যাচাই করা যাবে।")
    conditions = _conditions(db, deal)
    if not all(item["met"] for item in conditions[:3]):
        get_bank(db).refund(deal.id, deal.bayna_paisa, f"{deal.id}:failed-condition-refund")
        _record(db, deal, "refund_confirmed", str(user.id))
    elif all(item["met"] for item in conditions[:3]):
        _record(db, deal, "conditions_checked", str(user.id))
    db.commit()
    return _out(db, deal)


@router.post("/escrow/{deal_id}/registration")
def register_deed(deal_id: uuid.UUID, body: RegistrationIn, db: Db, user: CurrentUser):
    deal = _owned(db, deal_id, user)
    if deal.state != "conditions_met":
        raise HTTPException(409, "শর্ত যাচাইয়ের পর রেজিস্ট্রি নথিভুক্ত করুন।")
    deal.registration_deed_no, deal.registration_date = body.deed_no.strip(), body.date
    conditions = _conditions(db, deal)
    if not conditions[3]["met"]:
        db.rollback()
        raise HTTPException(422, "এই জমির extracted registered deed-এ নম্বর বা সময়সীমার তারিখ মেলেনি।")
    if all(item["met"] for item in conditions):
        _record(db, deal, "registration_recorded", str(user.id))
    db.commit()
    return _out(db, deal)


@router.post("/escrow/{deal_id}/release")
def release(deal_id: uuid.UUID, db: Db, user: CurrentUser):
    deal = _owned(db, deal_id, user)
    conditions = _conditions(db, deal)
    if not all(item["met"] for item in conditions):
        raise HTTPException(409, "সব শর্ত পূরণ না হওয়া পর্যন্ত টাকা ছাড়া যাবে না।")
    if deal.state != "registered":
        raise HTTPException(409, "রেজিস্ট্রি নথিভুক্ত হওয়ার আগে টাকা ছাড়া যাবে না।")
    get_bank(db).release(deal.id, deal.bayna_paisa, f"{deal.id}:release")
    _record(db, deal, "release_confirmed", str(user.id))
    db.commit()
    return _out(db, deal)


@router.post("/escrow/{deal_id}/refund")
def refund(deal_id: uuid.UUID, db: Db, user: CurrentUser):
    deal = _owned(db, deal_id, user)
    if deal.state not in {"funded", "conditions_met"}:
        raise HTTPException(409, "এই অবস্থায় টাকা ফেরত দেওয়া যাবে না।")
    if date.today() <= deal.deadline:
        raise HTTPException(409, "সময়সীমা পার হয়নি।")
    get_bank(db).refund(deal.id, deal.bayna_paisa, f"{deal.id}:deadline-refund")
    _record(db, deal, "deadline_passed", str(user.id))
    db.commit()
    return _out(db, deal)


@router.post("/escrow/{deal_id}/cancel")
def cancel(deal_id: uuid.UUID, db: Db, user: CurrentUser):
    deal = _owned(db, deal_id, user)
    _record(db, deal, "cancel", str(user.id))
    db.commit()
    return _out(db, deal)


@router.post("/escrow/{deal_id}/demo/expire")
def demo_expire(deal_id: uuid.UUID, db: Db, user: CurrentUser):
    if settings.bank_provider != "mock":
        raise HTTPException(404, "Not found")
    deal = _owned(db, deal_id, user)
    if deal.state not in {"funded", "conditions_met"}:
        raise HTTPException(409, "টাকা জমার পরই demo সময়সীমা পেরোনো দেখানো যাবে।")
    deal.deadline = date.today() - timedelta(days=1)
    db.commit()
    return get_deal(deal_id, db, user)


@router.get("/escrow/{deal_id}/baynanama.pdf")
def baynanama(deal_id: uuid.UUID, db: Db, user: CurrentUser):
    deal = _owned(db, deal_id, user)
    land = db.get(Land, deal.land_id)
    sellers = html.escape(", ".join(deal.seller_names))
    buyer = db.scalar(
        select(IdentityVerification)
        .where(
            IdentityVerification.user_id == deal.buyer_user_id,
            IdentityVerification.party == "buyer",
            IdentityVerification.status == "verified",
        )
        .order_by(IdentityVerification.created_at.desc())
        .limit(1)
    )
    buyer_name = html.escape(buyer.name_bn_as_per_nid if buyer else "ক্রেতা")
    mouza, dag, khatian = map(html.escape, (land.mouza, land.dag_no, land.khatian_no))
    conditions = _conditions(db, deal)
    rows = "".join(
        f"<li>{html.escape(item['label_bn'])}: {html.escape(item['detail_bn'])}</li>"
        for item in conditions
    )
    markup = f"""<!doctype html><html lang='bn'><meta charset='utf-8'><style>
    body{{font:18px sans-serif;margin:48px;color:#17231d}}h1{{color:#174b3b}}li{{margin:12px}}
    .draft{{border:2px solid #9a5c00;padding:16px;margin:24px 0;font-weight:bold}}
    </style><h1>বায়না-নামার খসড়া</h1><p>ক্রেতা: {buyer_name}</p><p>বিক্রেতা: {sellers}</p>
    <p>মৌজা: {mouza} · দাগ: {dag} · খতিয়ান: {khatian}</p>
    <p>মোট মূল্য: ৳{deal.price_paisa // 100:,} · বায়না: ৳{deal.bayna_paisa // 100:,}</p>
    <p>সময়সীমা: {deal.deadline.isoformat()}</p><h2>শর্ত</h2><ol>{rows}</ol>
    <p>সময়সীমায় শর্ত পূরণ না হলে জমাকৃত বায়না ক্রেতাকে ফেরত দেওয়া হবে।</p>
    <div class='draft'>খসড়া — রেজিস্ট্রির আগে আইনজীবী দিয়ে যাচাই করুন</div></html>"""
    return Response(
        render_report_pdf(markup),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="bayna-{deal.id}.pdf"'},
    )
