"""Backfill missing upload fingerprints from the currently stored bytes."""

import hashlib

from minio.error import S3Error
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Document
from app.services.storage import get_storage


def backfill() -> tuple[int, int]:
    changed = 0
    missing = 0
    with SessionLocal() as db:
        storage = get_storage()
        rows = db.scalars(select(Document).where(Document.content_sha256.is_(None))).all()
        for document in rows:
            try:
                stored_bytes = storage.download(document.file_key)
            except S3Error as exc:
                if exc.code != "NoSuchKey":
                    raise
                missing += 1
                continue
            document.content_sha256 = hashlib.sha256(stored_bytes).hexdigest()
            changed += 1
        db.commit()
    return changed, missing


if __name__ == "__main__":
    changed, missing = backfill()
    print(f"Backfilled {changed} document fingerprints; {missing} stored objects missing")
