import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdTimestampMixin


class DocumentAuditEvent(IdTimestampMixin, Base):
    __tablename__ = "document_audit_events"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    event: Mapped[str] = mapped_column(String(40))
    actor: Mapped[str] = mapped_column(String(80))
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
