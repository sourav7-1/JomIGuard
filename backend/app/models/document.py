import enum
import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdTimestampMixin


class DocType(enum.StrEnum):
    khatian = "khatian"
    deed = "deed"
    dcr = "dcr"
    heir_cert = "heir_cert"
    other = "other"


class DocStatus(enum.StrEnum):
    uploaded = "uploaded"
    processing = "processing"
    done = "done"
    failed = "failed"


class Document(IdTimestampMixin, Base):
    __tablename__ = "documents"

    land_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("lands.id", ondelete="SET NULL"), index=True
    )
    doc_type: Mapped[DocType]
    file_key: Mapped[str]  # MinIO object path
    original_filename: Mapped[str]
    status: Mapped[DocStatus] = mapped_column(default=DocStatus.uploaded)
