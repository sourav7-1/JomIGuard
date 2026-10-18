import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdTimestampMixin


class EscrowDeal(IdTimestampMixin, Base):
    __tablename__ = "escrow_deals"

    land_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lands.id", ondelete="CASCADE"), index=True
    )
    buyer_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    seller_names: Mapped[list] = mapped_column(JSONB)
    price_paisa: Mapped[int] = mapped_column(Integer)
    bayna_paisa: Mapped[int] = mapped_column(Integer)
    deadline: Mapped[date] = mapped_column(Date)
    state: Mapped[str] = mapped_column(String(24), default="draft")
    buyer_agreed: Mapped[bool] = mapped_column(Boolean, default=False)
    seller_agreed: Mapped[bool] = mapped_column(Boolean, default=False)
    conditions_snapshot: Mapped[list] = mapped_column(JSONB, default=list)
    registration_deed_no: Mapped[str | None] = mapped_column(String(100))
    registration_date: Mapped[date | None] = mapped_column(Date)
    seller_token_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


class EscrowEvent(IdTimestampMixin, Base):
    __tablename__ = "escrow_events"

    deal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("escrow_deals.id", ondelete="CASCADE"), index=True
    )
    event: Mapped[str] = mapped_column(String(32))
    from_state: Mapped[str] = mapped_column(String(24))
    to_state: Mapped[str] = mapped_column(String(24))
    actor: Mapped[str] = mapped_column(String(200))
    message_bn: Mapped[str] = mapped_column(Text)


class BankMockLedger(IdTimestampMixin, Base):
    __tablename__ = "bank_mock_ledger"

    deal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("escrow_deals.id", ondelete="CASCADE"), index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(120), unique=True)
    operation: Mapped[str] = mapped_column(String(16))
    amount_paisa: Mapped[int] = mapped_column(Integer)
