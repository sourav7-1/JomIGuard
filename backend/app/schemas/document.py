import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import DocStatus, DocType


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    land_id: uuid.UUID | None
    doc_type: DocType
    file_key: str
    original_filename: str
    status: DocStatus
    created_at: datetime
