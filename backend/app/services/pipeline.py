"""Process one uploaded document: load -> preprocess -> classify -> extract -> normalize -> store.

process_document() is called by the Celery task (app/workers/tasks.py) and holds all the logic.
Status lives on the document row (uploaded -> processing -> done | failed); every extraction run
adds an extractions row, so reprocessing keeps history.
"""

import uuid
from dataclasses import asdict
from datetime import UTC, datetime

import urllib3
from minio.error import S3Error
from sqlalchemy.orm import Session

from app.models import DocStatus, DocType, Document, Extraction, ExtractionStatus
from app.models.document import DocStep
from app.services.classify import check_user_label, classify_ocr
from app.services.extraction import BudgetExceeded, Extractor
from app.services.normalize import normalize_document
from app.services.ocr import ocr
from app.services.preprocess import PreprocessError, preprocess

# storage/network trouble: the document is marked failed and the error re-raised for a retry
TRANSIENT_ERRORS = (ConnectionError, TimeoutError, urllib3.exceptions.HTTPError, S3Error)

NOT_LAND_BN = "এই ছবিটি কোন জমির কাগজ বলে চেনা যায়নি"
OTHER_LABEL_BN = "এই ধরনের কাগজ থেকে তথ্য পড়া হয় না"
BAD_IMAGE_BN = "ছবিটি খোলা যায়নি"
EXTRACT_FAILED_BN = "কাগজ থেকে তথ্য পড়া যায়নি"
CONFIG_BN = "সার্ভারের extraction সেটিংস ঠিক নেই"
BUDGET_BN = "আজকের LLM খরচের দৈনিক সীমা (daily limit) শেষ হয়েছে; আগামীকাল আবার চেষ্টা করুন"


def make_extractor(name: str) -> Extractor:
    """Extractor from the EXTRACTOR setting: "llm" (default) or "tesseract_regex"."""
    if name == "llm":
        from app.services.extraction.llm import make_llm_extractor

        extractor = make_llm_extractor()  # LLM_PROVIDER: anthropic | gemini
    elif name == "tesseract_regex":
        from app.services.extraction.tesseract_regex import TesseractRegexExtractor

        extractor = TesseractRegexExtractor()
    else:
        raise ValueError(f"EXTRACTOR must be llm or tesseract_regex, not {name!r}")
    extractor.name = name
    return extractor


def load_bytes(storage, key: str) -> bytes:
    # ponytail: reads through the MinIO client; add Storage.download() when storage.py is in scope
    response = storage.client.get_object(storage.bucket, key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def field_flags(warnings) -> dict[str, list[str]]:
    flags: dict[str, list[str]] = {}
    for w in warnings:
        flags.setdefault(w.field_path, []).append(w.code)
    return flags


def _now() -> datetime:
    return datetime.now(UTC)


def process_document(
    document_id: uuid.UUID, db: Session, storage, extractor: Extractor, force: bool = False
) -> DocStatus | None:
    """-> the document's final status (None if the document does not exist)."""
    doc = db.get(Document, document_id)
    if doc is None:
        return None
    if doc.status == DocStatus.done and not force:
        return doc.status  # idempotent: a repeated task does nothing
    doc.status = DocStatus.processing
    doc.current_step = DocStep.reading
    doc.started_at, doc.finished_at = _now(), None
    doc.attempts = (doc.attempts or 0) + 1
    doc.error_message = doc.label_warning = None
    db.commit()

    def fail(message: str) -> DocStatus:
        db.rollback()  # drop anything half-written in this attempt
        failed = db.get(Document, document_id)
        failed.status, failed.error_message, failed.finished_at = DocStatus.failed, message, _now()
        db.commit()
        return failed.status

    try:
        data = load_bytes(storage, doc.file_key)
        try:
            gray = preprocess(data).gray
        except PreprocessError:
            return fail(BAD_IMAGE_BN)
        doc.current_step = DocStep.classifying
        db.commit()
        result = classify_ocr(lambda psm: ocr(gray, psm=psm).text)
        doc.detected_doc_type = DocType(result.doc_type)
        doc.classify_confidence = result.confidence
        if doc.doc_type is not None:
            warning = check_user_label(doc.doc_type, result)
            doc.label_warning = warning.message_bn if warning else None
            doc_type = doc.doc_type
        elif result.doc_type == "other":
            db.commit()  # keep the classifier's answer
            return fail(NOT_LAND_BN)
        else:
            doc_type = DocType(result.doc_type)
        if doc_type == DocType.other:
            return fail(OTHER_LABEL_BN)
        db.commit()

        doc.current_step = DocStep.extracting
        db.commit()
        ex = extractor.extract(data, doc_type.value)
        row = Extraction(
            document_id=doc.id,
            extractor=getattr(extractor, "name", type(extractor).__name__),
            model=ex.meta.model,
            prompt_version=ex.meta.prompt_version,
            cost_usd=ex.meta.cost_usd,
            latency_s=ex.meta.latency_s,
        )
        if ex.document is None:
            row.status, row.warnings, row.field_flags = ExtractionStatus.failed, [], {}
            db.add(row)
            doc.status, doc.finished_at = DocStatus.failed, _now()
            doc.error_message = f"{EXTRACT_FAILED_BN}: {ex.error}"
            db.commit()
            return doc.status
        doc.current_step = DocStep.normalizing
        db.commit()
        normalized = normalize_document(ex.document)
        row.data = normalized.doc.model_dump(mode="json")
        row.warnings = [asdict(w) for w in normalized.warnings]
        row.field_flags = field_flags(normalized.warnings)
        row.status = (
            ExtractionStatus.needs_review
            if normalized.warnings or doc.label_warning
            else ExtractionStatus.ok
        )
        db.add(row)
        doc.current_step = DocStep.finished
        doc.status, doc.finished_at = DocStatus.done, _now()
        db.commit()
        return doc.status
    except BudgetExceeded:
        return fail(BUDGET_BN)  # not retried: tomorrow's budget is a new day
    except TRANSIENT_ERRORS as e:
        fail(f"storage/network error: {type(e).__name__}")
        raise  # the Celery task retries these
    except Exception as e:  # noqa: BLE001  any other error: failed, with the reason
        return fail(f"{type(e).__name__}: {e}")


def process_with_settings(
    document_id: uuid.UUID, db: Session, storage, extractor_name: str, force: bool = False
) -> DocStatus | None:
    """Build the configured extractor, then process; a config error fails the document."""
    try:
        extractor = make_extractor(extractor_name)
    except ValueError as e:  # e.g. LLM_MODEL or prices not set
        doc = db.get(Document, document_id)
        if doc is None:
            return None
        doc.status, doc.finished_at = DocStatus.failed, _now()
        doc.error_message = f"{CONFIG_BN}: {e}"
        db.commit()
        return doc.status
    return process_document(document_id, db, storage, extractor, force)
