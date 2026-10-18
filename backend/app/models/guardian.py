import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdTimestampMixin


class GuardedLand(IdTimestampMixin, Base):
    __tablename__ = "guarded_lands"
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    label_bn: Mapped[str] = mapped_column(Text)
    district: Mapped[str]
    upazila: Mapped[str]
    mouza: Mapped[str]
    dag_no: Mapped[str]
    khatian_no: Mapped[str]
    baseline_snapshot_id: Mapped[uuid.UUID | None]
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GuardianSnapshot(IdTimestampMixin, Base):
    __tablename__ = "guardian_snapshots"
    guarded_land_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("guarded_lands.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    extraction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("extractions.id", ondelete="CASCADE")
    )
    taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    data: Mapped[dict] = mapped_column(JSONB)


class GuardianAlert(IdTimestampMixin, Base):
    __tablename__ = "guardian_alerts"
    guarded_land_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("guarded_lands.id", ondelete="CASCADE"), index=True
    )
    from_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("guardian_snapshots.id", ondelete="CASCADE")
    )
    to_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("guardian_snapshots.id", ondelete="CASCADE")
    )
    severity: Mapped[str] = mapped_column(Text)
    changes: Mapped[list] = mapped_column(JSONB)
    message_bn: Mapped[str] = mapped_column(Text)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
