import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdTimestampMixin


class IdentityVerification(IdTimestampMixin, Base):
    __tablename__ = "identity_verifications"

    land_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("lands.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    party: Mapped[str] = mapped_column(String(10))
    seller_name_on_deed: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(10))
    name_bn_as_per_nid: Mapped[str | None] = mapped_column(String(200))
    father_name_as_per_nid: Mapped[str | None] = mapped_column(String(200))
    provider: Mapped[str] = mapped_column(String(50))
    provider_ref: Mapped[str] = mapped_column(String(100))
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consent_version: Mapped[str] = mapped_column(String(40))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SellerLink(IdTimestampMixin, Base):
    __tablename__ = "seller_links"

    land_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lands.id", ondelete="CASCADE"), index=True
    )
    seller_name_on_deed: Mapped[str] = mapped_column(String(200))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consent_version: Mapped[str | None] = mapped_column(String(40))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    escrow_deal_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("escrow_deals.id", ondelete="CASCADE"), index=True
    )
