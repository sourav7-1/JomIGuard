import uuid

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.pipeline import TRANSIENT_ERRORS, process_with_settings
from app.services.storage import get_storage
from app.workers.celery_app import celery_app


@celery_app.task(
    autoretry_for=TRANSIENT_ERRORS,  # storage or network errors only
    retry_backoff=True,  # exponential: 1 s, 2 s, 4 s ...
    retry_kwargs={"max_retries": 3},
)
def process_document_task(document_id: str, force: bool = False) -> str | None:
    with SessionLocal() as db:
        status = process_with_settings(
            uuid.UUID(document_id), db, get_storage(), settings.extractor, force
        )
    return status.value if status else None
