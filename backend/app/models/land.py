import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdTimestampMixin


class Land(IdTimestampMixin, Base):
    __tablename__ = "lands"

    district: Mapped[str]
    upazila: Mapped[str]
    mouza: Mapped[str]
    dag_no: Mapped[str]  # string: values like "305/1"
    khatian_no: Mapped[str]
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
