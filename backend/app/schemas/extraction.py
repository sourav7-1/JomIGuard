import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.extraction import ExtractionStatus
from app.schemas.extracted import ExtractedDocument


class ExtractionWarningOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    code: str
    field_path: str
    message_bn: str


class ExtractionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    extractor: str
    model: str | None = None
    prompt_version: str | None = None
    status: ExtractionStatus
    data: ExtractedDocument | dict[str, Any] | None = None
    warnings: list[ExtractionWarningOut] = Field(default_factory=list)
    field_flags: dict[str, Any] = Field(default_factory=dict)
    handwritten: bool = False
    created_at: datetime
