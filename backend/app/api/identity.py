import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.auth import authenticated_user
from app.core.config import settings
from app.db.session import get_db
from app.models import EscrowDeal, IdentityVerification, Land, SellerLink, User
from app.schemas.identity import (
    BuyerVerificationIn,
    ConsentIn,
    IdentityVerificationOut,
    SellerLinkCreate,
    SellerLinkCreated,
    VerificationCompleteIn,
)
from app.services.identity import get_provider
from app.services.land_case import load_land_case
from app.services.rules.names import names_match

router = APIRouter(tags=["identity"])
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(authenticated_user)]
TOKEN_LIFETIME = timedelta(days=7)
CONSENT_VERSION = "identity-demo-v1"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def _live_link(db: Session, token: str) -> SellerLink:
    link = db.scalar(select(SellerLink).where(SellerLink.token_hash == _token_hash(token)))
    now = datetime.now(UTC)
    if link is None or link.used_at is not None or _utc(link.expires_at) <= now:
        raise HTTPException(410, "এই যাচাইয়ের link আর ব্যবহার করা যাবে না।")
    return link


@router.post("/lands/{land_id}/seller-links", response_model=SellerLinkCreated, status_code=201)
def create_seller_link(land_id: uuid.UUID, body: SellerLinkCreate, db: Db, user: CurrentUser):
    land = db.get(Land, land_id)
    if land is None or land.owner_id != user.id:
        raise HTTPException(404, "Land not found")
    case = load_land_case(db, land_id)
    deed = case.proposed_deed
    if deed is None or not any(
        names_match(body.seller_name_on_deed.strip(), seller.name)[0]
        for seller in deed.data.sellers
    ):
        raise HTTPException(422, "দলিলে এই বিক্রেতার নাম পাওয়া যায়নি।")

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + TOKEN_LIFETIME
    escrow = db.scalar(
        select(EscrowDeal)
        .where(
            EscrowDeal.land_id == land_id,
            EscrowDeal.buyer_user_id == user.id,
            EscrowDeal.state.in_(["draft", "agreed"]),
        )
        .order_by(EscrowDeal.created_at.desc())
        .limit(1)
    )
    db.add(
        SellerLink(
            land_id=land_id,
            seller_name_on_deed=body.seller_name_on_deed.strip(),
            token_hash=_token_hash(token),
            expires_at=expires_at,
            escrow_deal_id=escrow.id if escrow else None,
        )
    )
    db.commit()
    return SellerLinkCreated(url=f"/verify/{token}", expires_at=expires_at)


@router.get("/verify/{token}")
def seller_link_details(token: str, db: Db):
    link = _live_link(db, token)
    land = db.get(Land, link.land_id)
    return {
        "mouza": land.mouza,
        "dag_no": land.dag_no,
        "escrow_agreement_requested": link.escrow_deal_id is not None,
        "message_bn": "একজন ক্রেতা এই জমির বিক্রেতার পরিচয় যাচাই করতে বলেছেন।",
    }


@router.post("/verify/{token}/consent")
def seller_consent(token: str, body: ConsentIn, db: Db):
    link = _live_link(db, token)
    if link.consent_at is None:
        link.consent_at = datetime.now(UTC)
        link.consent_version = CONSENT_VERSION
        db.commit()
    return {"consented": True}


@router.post("/verify/{token}/complete", response_model=IdentityVerificationOut)
def complete_seller_verification(token: str, body: VerificationCompleteIn, db: Db):
    link = _live_link(db, token)
    if link.consent_at is None:
        raise HTTPException(409, "আগে সম্মতি দিন।")

    provider = get_provider()
    if provider.name != settings.identity_provider:
        raise HTTPException(503, "পরিচয় যাচাইয়ের provider প্রস্তুত নয়।")
    result = provider.verify(body.name.strip(), body.father_name.strip(), body.outcome)
    now = datetime.now(UTC)
    consumed = db.execute(
        update(SellerLink)
        .where(
            SellerLink.id == link.id,
            SellerLink.used_at.is_(None),
            SellerLink.expires_at > now,
            SellerLink.consent_at.is_not(None),
        )
        .values(used_at=now)
    )
    if consumed.rowcount != 1:
        db.rollback()
        raise HTTPException(410, "এই যাচাইয়ের link আর ব্যবহার করা যাবে না।")
    row = IdentityVerification(
        land_id=link.land_id,
        user_id=None,
        party="seller",
        seller_name_on_deed=link.seller_name_on_deed,
        status=result.status,
        name_bn_as_per_nid=result.name_bn_as_per_nid,
        father_name_as_per_nid=result.father_name_as_per_nid,
        provider=result.provider,
        provider_ref=result.provider_ref,
        consent_at=link.consent_at,
        consent_version=link.consent_version or CONSENT_VERSION,
        verified_at=result.verified_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.post("/me/verification", response_model=IdentityVerificationOut, status_code=201)
def verify_buyer(body: BuyerVerificationIn, db: Db, user: CurrentUser):
    result = get_provider().verify(body.name.strip(), body.father_name.strip(), body.outcome)
    row = IdentityVerification(
        land_id=None,
        user_id=user.id,
        party="buyer",
        seller_name_on_deed=None,
        status=result.status,
        name_bn_as_per_nid=result.name_bn_as_per_nid,
        father_name_as_per_nid=result.father_name_as_per_nid,
        provider=result.provider,
        provider_ref=result.provider_ref,
        consent_at=datetime.now(UTC),
        consent_version=CONSENT_VERSION,
        verified_at=result.verified_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/me/verification", response_model=list[IdentityVerificationOut])
def my_verifications(db: Db, user: CurrentUser):
    return db.scalars(
        select(IdentityVerification)
        .where(IdentityVerification.user_id == user.id, IdentityVerification.party == "buyer")
        .order_by(IdentityVerification.created_at.desc())
    ).all()


@router.delete("/me/verification/{verification_id}", status_code=204)
def delete_buyer_verification(verification_id: uuid.UUID, db: Db, user: CurrentUser):
    row = db.get(IdentityVerification, verification_id)
    if row is None or row.party != "buyer" or row.user_id != user.id:
        raise HTTPException(404, "Verification not found")
    db.delete(row)
    db.commit()


@router.delete("/verify/{token}", status_code=204)
def delete_seller_verification(token: str, db: Db):
    link = db.scalar(select(SellerLink).where(SellerLink.token_hash == _token_hash(token)))
    if link is None or link.used_at is None:
        raise HTTPException(410, "এই যাচাইয়ের link আর ব্যবহার করা যাবে না।")
    row = db.scalar(
        select(IdentityVerification)
        .where(
            IdentityVerification.land_id == link.land_id,
            IdentityVerification.party == "seller",
            IdentityVerification.seller_name_on_deed == link.seller_name_on_deed,
            IdentityVerification.created_at >= link.created_at,
        )
        .order_by(IdentityVerification.created_at.desc())
        .limit(1)
    )
    if row is not None:
        db.delete(row)
    db.delete(link)
    db.commit()
