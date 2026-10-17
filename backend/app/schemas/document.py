import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import DocStatus, DocType, ExtractionStatus
from app.models.document import DocStep

STATUS_LABELS_BN: dict[str, str] = {
    # status
    "uploaded": "আপলোড হয়েছে",
    "processing": "পড়া হচ্ছে",
    "done": "পড়া শেষ",
    "failed": "পড়া যায়নি",
    # steps
    "queued": "অপেক্ষমাণ",
    "reading": "কাগজ পড়া হচ্ছে",
    "classifying": "ধরন শনাক্ত করা হচ্ছে",
    "extracting": "তথ্য বের করা হচ্ছে",
    "normalizing": "তথ্য যাচাই করা হচ্ছে",
    "finished": "পড়া শেষ",
}
LABELS_BN = STATUS_LABELS_BN


def count_needs_review(flags_by_field: dict | None) -> int:
    if not flags_by_field:
        return 0
    count = 0
    for flags in flags_by_field.values():
        if isinstance(flags, str):
            if flags.lower() in ("low", "medium"):
                count += 1
        elif isinstance(flags, (list, tuple, set)):
            if any(str(f).lower() in ("low", "medium") for f in flags):
                count += 1
        elif isinstance(flags, dict):
            if any(str(v).lower() in ("low", "medium") for v in flags.values()):
                count += 1
    return count


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    land_id: uuid.UUID | None
    doc_type: DocType | None
    file_key: str
    original_filename: str
    status: DocStatus
    current_step: DocStep = DocStep.queued
    created_at: datetime
    updated_at: datetime | None = None
    detected_doc_type: DocType | None = None
    classify_confidence: float | None = None
    label_warning: str | None = None
    error_message: str | None = None
    attempts: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None


class LatestExtractionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: ExtractionStatus
    needs_review_count: int
    warnings_count: int


class DocumentStatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    doc_type: DocType | None
    detected_doc_type: DocType | None = None
    classify_confidence: float | None = None
    status: DocStatus
    status_label_bn: str
    current_step: DocStep
    step_label_bn: str
    label_warning: str | None = None
    error_message: str | None = None
    attempts: int = 0
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    updated_at: datetime | None = None
    is_stale: bool = False
    latest_extraction: LatestExtractionOut | None = None
    poll_after_s: int | None = None


class DocumentListOut(BaseModel):
    items: list[DocumentOut]
    total: int
