import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
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


class DocStep(enum.StrEnum):
    queued = "queued"
    reading = "reading"
    classifying = "classifying"
    extracting = "extracting"
    normalizing = "normalizing"
    finished = "finished"


class Document(IdTimestampMixin, Base):
    __tablename__ = "documents"

    land_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("lands.id", ondelete="SET NULL"), index=True
    )
    doc_type: Mapped[DocType | None]  # as chosen by the user; None if they did not say
    file_key: Mapped[str]  # MinIO object path
    original_filename: Mapped[str]
    status: Mapped[DocStatus] = mapped_column(default=DocStatus.uploaded)
    current_step: Mapped[DocStep] = mapped_column(default=DocStep.queued, server_default="queued")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # background processing (services/pipeline.py)
    detected_doc_type: Mapped[DocType | None]  # from the classifier
    classify_confidence: Mapped[float | None]
    label_warning: Mapped[str | None] = mapped_column(Text)  # Bangla, when label and image disagree
    error_message: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(default=0, server_default="0")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
