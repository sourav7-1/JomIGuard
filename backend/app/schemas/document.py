import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import DocStatus, DocType


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    land_id: uuid.UUID | None
    doc_type: DocType | None
    file_key: str
    original_filename: str
    status: DocStatus
    created_at: datetime
    detected_doc_type: DocType | None = None
    classify_confidence: float | None = None
    label_warning: str | None = None
    error_message: str | None = None
    attempts: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None
