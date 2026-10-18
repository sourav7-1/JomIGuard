import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import PureWindowsPath
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from minio import Minio
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import authenticated_user
from app.core.config import settings
from app.db.session import get_db
from app.models import DocStatus, DocType, Document, DocumentAuditEvent, Extraction, Land, User
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
CurrentUser = Annotated[User, Depends(authenticated_user)]


def _owned_document(db: Session, document_id: uuid.UUID, user: User) -> Document:
    doc = db.get(Document, document_id)
    if doc is None or doc.owner_id != user.id:
        raise HTTPException(404, "Document not found")
    return doc


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
    user: CurrentUser,
    doc_type: Annotated[DocType | None, Form()] = None,
    land_id: Annotated[uuid.UUID | None, Form()] = None,
    source_type: Annotated[str, Form()] = "user_upload",
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, f"Unsupported file type: {file.content_type}")
    if source_type not in {"user_upload", "certified_copy_user_claim"}:
        raise HTTPException(422, "Official source verification is unavailable")
    if (
        land_id
        and db.scalar(select(Land.id).where(Land.id == land_id, Land.owner_id == user.id)) is None
    ):
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
        owner_id=user.id,
        doc_type=doc_type,
        file_key=key,
        content_sha256=hashlib.sha256(data).hexdigest(),
        source_type=source_type,
        original_filename=filename,
        status=DocStatus.uploaded,
        current_step=DocStep.queued,
    )
    db.add(doc)
    db.add(
        DocumentAuditEvent(
            document_id=doc_id,
            event="uploaded",
            actor=str(user.id),
            details={"source_type": source_type},
        )
    )
    db.commit()
    process_document_task.delay(str(doc.id))  # only after the commit: the worker must find it
    return doc


@router.get("", response_model=DocumentListOut)
def list_documents(
    db: Db,
    user: CurrentUser,
    status: Annotated[DocStatus | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    base = select(Document).where(Document.owner_id == user.id)
    count_q = select(func.count()).select_from(Document).where(Document.owner_id == user.id)
    if status is not None:
        base = base.where(Document.status == status)
        count_q = count_q.where(Document.status == status)
    total = db.scalar(count_q) or 0
    items = db.scalars(base.order_by(Document.created_at.desc()).offset(offset).limit(limit)).all()
    return DocumentListOut(items=items, total=total)


@router.post("/{document_id}/reprocess", response_model=DocumentOut, status_code=202)
def reprocess_document(document_id: uuid.UUID, db: Db, user: CurrentUser):
    doc = _owned_document(db, document_id, user)
    process_document_task.delay(str(doc.id), force=True)
    return doc


class DocumentPatch(BaseModel):
    land_id: uuid.UUID | None


@router.patch("/{document_id}", response_model=DocumentOut)
def attach_document(document_id: uuid.UUID, body: DocumentPatch, db: Db, user: CurrentUser):
    """Attach a document to a land (land_id) or detach it (null)."""
    doc = _owned_document(db, document_id, user)
    if (
        body.land_id
        and db.scalar(select(Land.id).where(Land.id == body.land_id, Land.owner_id == user.id))
        is None
    ):
        raise HTTPException(404, "Land not found")
    doc.land_id = body.land_id
    db.commit()
    return doc


@router.get("/{document_id}", response_model=DocumentStatusOut)
def get_document(document_id: uuid.UUID, db: Db, user: CurrentUser):
    doc = _owned_document(db, document_id, user)

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
    user: CurrentUser,
    history: bool = False,
):
    doc = _owned_document(db, document_id, user)
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


class FingerprintVerificationOut(BaseModel):
    stored_sha256: str | None
    current_sha256: str
    unchanged_since_upload: bool | None
    official_source_verified: bool = False
    notice_bn: str = "সরকারি উৎসে আসলত্ব যাচাই করা হয়নি।"


@router.post("/{document_id}/fingerprint/verify", response_model=FingerprintVerificationOut)
def verify_document_fingerprint(
    document_id: uuid.UUID,
    db: Db,
    storage: Annotated[Storage, Depends(get_storage)],
    user: CurrentUser,
):
    doc = _owned_document(db, document_id, user)
    current = hashlib.sha256(storage.download(doc.file_key)).hexdigest()
    return FingerprintVerificationOut(
        stored_sha256=doc.content_sha256,
        current_sha256=current,
        unchanged_since_upload=(current == doc.content_sha256 if doc.content_sha256 else None),
    )


@router.get("/{document_id}/file", response_model=DocumentFileOut)
def get_document_file(
    document_id: uuid.UUID,
    db: Db,
    storage: Annotated[Storage, Depends(get_storage)],
    user: CurrentUser,
):
    """Return a short-lived presigned URL for the original document upload."""
    doc = _owned_document(db, document_id, user)

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
    user: CurrentUser,
):
    """Apply human corrections and field confirmations, saving a new extraction row."""
    doc = _owned_document(db, document_id, user)

    latest = db.scalars(
        select(Extraction)
        .where(Extraction.document_id == doc.id)
        .order_by(Extraction.created_at.desc(), Extraction.id.desc())
    ).first()
    if latest is None:
        raise HTTPException(404, "Extraction not found")

    return apply_corrections(doc, latest, body.edits, body.confirms, db, str(user.id))


class ProvenancePatch(BaseModel):
    source_type: str


@router.patch("/{document_id}/provenance")
def update_document_provenance(
    document_id: uuid.UUID, body: ProvenancePatch, db: Db, user: CurrentUser
):
    if body.source_type not in {"user_upload", "certified_copy_user_claim"}:
        raise HTTPException(422, "Official source verification is unavailable")
    doc = _owned_document(db, document_id, user)
    previous = doc.source_type or "user_upload"
    if previous != body.source_type:
        doc.source_type = body.source_type
        db.add(
            DocumentAuditEvent(
                document_id=doc.id,
                event="provenance_changed",
                actor=str(user.id),
                details={"from": previous, "to": body.source_type},
            )
        )
        db.commit()
    return {"source_type": doc.source_type, "official_source_verified": False}
