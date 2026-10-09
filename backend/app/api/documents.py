import uuid
from pathlib import PureWindowsPath
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import DocStatus, DocType, Document, Land
from app.schemas.document import DocumentOut
from app.services.storage import Storage, get_storage

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
    doc_type: Annotated[DocType, Form()],
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
    )
    db.add(doc)
    db.commit()
    return doc


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Db):
    return db.scalars(select(Document).order_by(Document.created_at.desc())).all()


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: uuid.UUID, db: Db):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    return doc
