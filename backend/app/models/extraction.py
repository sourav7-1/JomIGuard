import enum
import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdTimestampMixin


class ExtractionStatus(enum.StrEnum):
    ok = "ok"
    needs_review = "needs_review"  # normalize warnings or a label/classifier disagreement
    failed = "failed"


class Extraction(IdTimestampMixin, Base):
    """One extraction run of a document; reprocessing adds a row (history is kept)."""

    __tablename__ = "extractions"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    extractor: Mapped[str]  # "llm" | "tesseract_regex"
    model: Mapped[str | None]
    prompt_version: Mapped[str | None]
    status: Mapped[ExtractionStatus]
    data: Mapped[dict | None] = mapped_column(JSONB)  # normalized ExtractedDocument
    warnings: Mapped[list] = mapped_column(JSONB, default=list)  # normalize warnings
    field_flags: Mapped[dict] = mapped_column(JSONB, default=dict)  # field_path -> [codes]
    cost_usd: Mapped[float] = mapped_column(default=0.0)
    latency_s: Mapped[float] = mapped_column(default=0.0)
