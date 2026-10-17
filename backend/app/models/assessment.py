import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdTimestampMixin


class LandAssessment(IdTimestampMixin, Base):
    """One stored assessment of a land (schemas/assessment.py); every run adds a row."""

    __tablename__ = "assessments"

    land_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lands.id", ondelete="CASCADE"), index=True
    )
    engine_version: Mapped[str]
    risk_level: Mapped[str]  # high | medium | low
    result: Mapped[dict] = mapped_column(JSONB)  # the full Assessment
