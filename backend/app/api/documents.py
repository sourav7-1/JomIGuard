import uuid
from datetime import UTC, datetime, timedelta
from pathlib import PureWindowsPath
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from minio import Minio
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import DocStatus, DocType, Document, Extraction, Land
from app.models.document import DocStep
from app.schemas.document import (
    STATUS_LABELS_BN,
    DocumentListOut,
    DocumentOut,
    DocumentStatusOut,
    LatestExtractionOut,
    count_needs_review,
)
from app.schemas.extraction import ExtractionOut
from app.services.corrections import CorrectionRequest, apply_corrections
from app.services.storage import Storage, get_storage
from app.workers.tasks import process_document_task

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "application/pdf"}
MAX_BYTES = 10 * 1024 * 1024
CHUNK = 1024 * 1024

Db = Annotated[Session, Depends(get_db)]


def read_capped(file: UploadFile) -> bytes:
    # ponytail: Starlette spools the whole part to a temp file before this runs;
    # add a Content-Length check in middleware if huge uploads start costing disk/bandwidth.
    buf = bytearray()
    while chunk := file.file.read(CHUNK):
        buf += chunk
        if len(buf) > MAX_BYTES:
            raise HTTPException(413, "File larger than 10 MB")
    return bytes(buf)


@router.post("", response_model=DocumentOut, status_code=201)
def upload_document(
    db: Db,
    storage: Annotated[Storage, Depends(get_storage)],
    file: Annotated[UploadFile, File()],
    doc_type: Annotated[DocType | None, Form()] = None,
    land_id: Annotated[uuid.UUID | None, Form()] = None,
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, f"Unsupported file type: {file.content_type}")
    if land_id and db.get(Land, land_id) is None:
        raise HTTPException(404, "Land not found")

    data = read_capped(file)
    # strip client-supplied paths ("../x", "C:\x") so the key stays under the doc id
    filename = PureWindowsPath(file.filename or "").name or "file"
    doc_id = uuid.uuid4()
    key = f"{doc_id}/{filename}"
    storage.upload(key, data, file.content_type)

    doc = Document(
        id=doc_id,
        land_id=land_id,
        doc_type=doc_type,
        file_key=key,
        original_filename=filename,
        status=DocStatus.uploaded,
        current_step=DocStep.queued,
    )
    db.add(doc)
    db.commit()
    process_document_task.delay(str(doc.id))  # only after the commit: the worker must find it
    return doc


@router.get("", response_model=DocumentListOut)
def list_documents(
    db: Db,
    status: Annotated[DocStatus | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    base = select(Document)
    count_q = select(func.count()).select_from(Document)
    if status is not None:
        base = base.where(Document.status == status)
        count_q = count_q.where(Document.status == status)
    total = db.scalar(count_q) or 0
    items = db.scalars(base.order_by(Document.created_at.desc()).offset(offset).limit(limit)).all()
    return DocumentListOut(items=items, total=total)


@router.post("/{document_id}/reprocess", response_model=DocumentOut, status_code=202)
def reprocess_document(document_id: uuid.UUID, db: Db):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    process_document_task.delay(str(doc.id), force=True)
    return doc


class DocumentPatch(BaseModel):
    land_id: uuid.UUID | None


@router.patch("/{document_id}", response_model=DocumentOut)
def attach_document(document_id: uuid.UUID, body: DocumentPatch, db: Db):
    """Attach a document to a land (land_id) or detach it (null)."""
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    if body.land_id and db.get(Land, body.land_id) is None:
        raise HTTPException(404, "Land not found")
    doc.land_id = body.land_id
    db.commit()
    return doc


@router.get("/{document_id}", response_model=DocumentStatusOut)
def get_document(document_id: uuid.UUID, db: Db):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")

    latest = db.scalars(
        select(Extraction)
        .where(Extraction.document_id == doc.id)
        .order_by(Extraction.created_at.desc(), Extraction.id.desc())
    ).first()

    latest_extraction = None
    if latest is not None:
        latest_extraction = LatestExtractionOut(
            id=latest.id,
            status=latest.status,
            needs_review_count=count_needs_review(latest.field_flags),
            warnings_count=len(latest.warnings or []),
        )

    now = datetime.now(UTC)
    updated_at = doc.updated_at
    if updated_at is not None and updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=UTC)

    is_stale = False
    if doc.status == DocStatus.processing and updated_at is not None:
        is_stale = (now - updated_at).total_seconds() > settings.stale_after_minutes * 60

    poll_after_s = 2 if doc.status == DocStatus.processing else None

    return DocumentStatusOut(
        id=doc.id,
        original_filename=doc.original_filename,
        doc_type=doc.doc_type,
        detected_doc_type=doc.detected_doc_type,
        classify_confidence=doc.classify_confidence,
        status=doc.status,
        status_label_bn=STATUS_LABELS_BN.get(doc.status, ""),
        current_step=doc.current_step,
        step_label_bn=STATUS_LABELS_BN.get(doc.current_step, ""),
        label_warning=doc.label_warning,
        error_message=doc.error_message,
        attempts=doc.attempts,
        created_at=doc.created_at,
        started_at=doc.started_at,
        finished_at=doc.finished_at,
        updated_at=doc.updated_at,
        is_stale=is_stale,
        latest_extraction=latest_extraction,
        poll_after_s=poll_after_s,
    )


@router.get("/{document_id}/extraction", response_model=ExtractionOut | list[ExtractionOut])
def get_document_extraction(
    document_id: uuid.UUID,
    db: Db,
    history: bool = False,
):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    if doc.status != DocStatus.done:
        raise HTTPException(409, "কাগজ পড়া এখনও শেষ হয়নি")

    q = (
        select(Extraction)
        .where(Extraction.document_id == doc.id)
        .order_by(Extraction.created_at.desc(), Extraction.id.desc())
    )
    if history:
        return db.scalars(q).all()
    latest = db.scalars(q).first()
    if latest is None:
        raise HTTPException(404, "Extraction not found")
    return latest


class DocumentFileOut(BaseModel):
    url: str


@router.get("/{document_id}/file", response_model=DocumentFileOut)
def get_document_file(
    document_id: uuid.UUID,
    db: Db,
    storage: Annotated[Storage, Depends(get_storage)],
):
    """Return a short-lived presigned URL for the original document upload."""
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")

    if hasattr(storage, "client") and isinstance(storage.client, Minio):
        endpoint = settings.minio_endpoint
        if endpoint.startswith("minio:"):
            endpoint = "localhost:" + endpoint.split(":", 1)[1]
        client = Minio(
            endpoint,
            access_key=settings.minio_root_user,
            secret_key=settings.minio_root_password,
            secure=False,
            region="us-east-1",
        )
        url = client.presigned_get_object(
            storage.bucket, doc.file_key, expires=timedelta(minutes=15)
        )
    else:
        bucket = getattr(storage, "bucket", "documents")
        url = f"http://localhost:9000/{bucket}/{doc.file_key}"

    return DocumentFileOut(url=url)


@router.patch("/{document_id}/extraction", response_model=ExtractionOut)
def patch_document_extraction(
    document_id: uuid.UUID,
    body: CorrectionRequest,
    db: Db,
):
    """Apply human corrections and field confirmations, saving a new extraction row."""
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")

    latest = db.scalars(
        select(Extraction)
        .where(Extraction.document_id == doc.id)
        .order_by(Extraction.created_at.desc(), Extraction.id.desc())
    ).first()
    if latest is None:
        raise HTTPException(404, "Extraction not found")

    return apply_corrections(doc, latest, body.edits, body.confirms, db)
