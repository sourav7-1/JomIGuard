import enum
import uuid

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdTimestampMixin


class SatelliteCheckStatus(enum.StrEnum):
    pending = "pending"
    ok = "ok"
    failed = "failed"


class SatelliteCheck(IdTimestampMixin, Base):
    """One run of the sentinel analyze-area service for a land; every run adds a row."""

    __tablename__ = "satellite_checks"

    land_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lands.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(
        String(10), default=SatelliteCheckStatus.pending, server_default="pending"
    )
    buffer_m: Mapped[float] = mapped_column(default=200.0, server_default="200")
    years: Mapped[list[int] | None] = mapped_column(JSON)  # None = service default (2019..2025)
    result: Mapped[dict | None] = mapped_column(JSONB)  # the full analyze-area response
    error: Mapped[str | None] = mapped_column(Text)
