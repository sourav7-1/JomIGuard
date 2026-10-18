"""services/pipeline.py with fake storage, fake extractor and a fixed classifier answer."""

import json
import uuid
from decimal import Decimal
from pathlib import Path

import cv2
import numpy as np
import pytest
from conftest import TestSession
from sqlalchemy import select

from app.models import DocStatus, DocType, Document, Extraction, ExtractionStatus
from app.models.document import DocStep
from app.schemas.extracted import KhatianData
from app.services import pipeline
from app.services.classify import ClassifyResult
from app.services.extraction import BudgetExceeded, ExtractionMeta, ExtractionResult

SAMPLE = Path(__file__).parents[1] / "fixtures/samples/khatian.json"
DERIVED = {"name_normalized", "share_fraction", "share_shatangsho", "plot_total_area_shatangsho",
           "khatian_share_fraction", "area_shatangsho", "total_area_shatangsho"}  # fmt: skip
PNG = cv2.imencode(".png", np.full((600, 500), 255, np.uint8))[1].tobytes()


def printed_khatian() -> KhatianData:
    def strip(node):
        if isinstance(node, dict):
            return {k: strip(v) for k, v in node.items() if k not in DERIVED}
        if isinstance(node, list):
            return [strip(v) for v in node]
        return node

    return KhatianData.model_validate(strip(json.loads(SAMPLE.read_text(encoding="utf-8"))))


class FakeStorage:
    bucket = "documents"

    def __init__(self, objects: dict[str, bytes]):
        self.objects = objects
        self.client = self

    def get_object(self, bucket, key):
        data = self.objects[key]
        return type("R", (), {"read": lambda s: data, "close": lambda s: None,
                              "release_conn": lambda s: None})()  # fmt: skip


class FakeExtractor:
    name = "fake"

    def __init__(self, result=None, raises=None):
        self.result, self.raises, self.calls = result, raises, []

    def extract(self, image_bytes, doc_type):
        self.calls.append(doc_type)
        if self.raises:
            raise self.raises
        return self.result or ExtractionResult(
            document=printed_khatian(),
            meta=ExtractionMeta(model="fake-model", cost_usd=0.01, latency_s=1.5,
                                prompt_version="v1"),
        )  # fmt: skip


@pytest.fixture
def db():
    with TestSession() as session:
        yield session


@pytest.fixture
def classified(monkeypatch):
    """Set what the classifier answers (no OCR runs)."""

    def set_answer(doc_type: str, confidence: float = 0.9):
        monkeypatch.setattr(
            pipeline, "classify_ocr", lambda read_text: ClassifyResult(doc_type, confidence)
        )

    set_answer("khatian")
    return set_answer


def new_document(db, doc_type: DocType | None = DocType.khatian) -> Document:
    doc_id = uuid.uuid4()
    doc = Document(id=doc_id, doc_type=doc_type, file_key=f"{doc_id}/k.png",
                   original_filename="k.png")  # fmt: skip
    db.add(doc)
    db.commit()
    return doc


def run(db, doc, extractor=None, force=False):
    storage = FakeStorage({doc.file_key: PNG})
    return pipeline.process_document(doc.id, db, storage, extractor or FakeExtractor(), force)


def extractions(db, doc) -> list[Extraction]:
    return db.scalars(select(Extraction).where(Extraction.document_id == doc.id)).all()


def test_happy_path_stores_normalized_data(db, classified):
    doc = new_document(db)
    assert run(db, doc) == DocStatus.done
    db.refresh(doc)
    assert doc.detected_doc_type == DocType.khatian and doc.classify_confidence == 0.9
    assert doc.attempts == 1 and doc.started_at and doc.finished_at
    assert doc.label_warning is None and doc.error_message is None
    [row] = extractions(db, doc)
    assert row.status == ExtractionStatus.ok and row.extractor == "fake"
    assert (row.model, row.prompt_version, row.cost_usd, row.latency_s) == (
        "fake-model", "v1", 0.01, 1.5)  # fmt: skip
    owner = row.data["owners"][0]
    assert Decimal(owner["share_shatangsho"]) == Decimal("6")  # filled by normalize
    assert owner["name_normalized"] == "রহিম উদ্দিন"
    assert row.warnings == [] and row.field_flags == {}


def test_handwritten_lowers_every_field_confidence_and_is_stored(db, classified):
    doc = new_document(db)
    result = ExtractionResult(document=printed_khatian(), handwritten=True)
    assert run(db, doc, FakeExtractor(result=result)) == DocStatus.done
    row = extractions(db, doc)[0]
    assert row.handwritten is True
    assert row.field_flags["owners[0].name"] == ["medium"]
    assert row.field_flags["owners[0].share_shatangsho"] == ["medium"]


def test_lower_field_confidence_degrades_each_level_once_and_keeps_other_flags():
    flags = {"a": ["high"], "b.c": ["medium", "format_warning"], "c": ["low"]}
    assert pipeline.lower_field_confidence({"a": 1, "b": {"c": 2}, "d": [3]}, flags) == {
        "a": ["medium"],
        "b.c": ["low", "format_warning"],
        "c": ["low"],
        "d[0]": ["medium"],
    }


def test_label_disagreement_warns_and_uses_the_user_label(db, classified):
    classified("deed")
    doc = new_document(db, DocType.khatian)
    extractor = FakeExtractor()
    assert run(db, doc, extractor) == DocStatus.done
    db.refresh(doc)
    assert doc.detected_doc_type == DocType.deed
    assert "খতিয়ান" in doc.label_warning and "দলিল" in doc.label_warning
    assert extractor.calls == ["khatian"]
    assert extractions(db, doc)[0].status == ExtractionStatus.needs_review


def test_no_label_uses_the_classifier(db, classified):
    doc = new_document(db, None)
    extractor = FakeExtractor()
    assert run(db, doc, extractor) == DocStatus.done
    assert extractor.calls == ["khatian"]


def test_no_label_and_not_a_land_document_fails(db, classified):
    classified("other", 0.0)
    doc = new_document(db, None)
    extractor = FakeExtractor()
    assert run(db, doc, extractor) == DocStatus.failed
    db.refresh(doc)
    assert doc.error_message == "এই ছবিটি কোন জমির কাগজ বলে চেনা যায়নি"
    assert doc.detected_doc_type == DocType.other
    assert extractor.calls == [] and extractions(db, doc) == []


def test_extractor_error_fails_with_message(db, classified):
    doc = new_document(db)
    bad = FakeExtractor(ExtractionResult(error="invalid output: 3 errors",
                                         meta=ExtractionMeta(model="fake-model")))  # fmt: skip
    assert run(db, doc, bad) == DocStatus.failed
    db.refresh(doc)
    assert "invalid output" in doc.error_message
    [row] = extractions(db, doc)
    assert row.status == ExtractionStatus.failed and row.data is None


def test_budget_exceeded_fails_without_raising(db, classified):
    doc = new_document(db)
    status = run(db, doc, FakeExtractor(raises=BudgetExceeded("over")))  # no exception: no retry
    assert status == DocStatus.failed
    db.refresh(doc)
    assert "daily limit" in doc.error_message and extractions(db, doc) == []


def test_storage_error_marks_failed_and_reraises_for_retry(db, classified):
    doc = new_document(db)
    storage = FakeStorage({})

    def broken(bucket, key):
        raise ConnectionError("minio down")

    storage.get_object = broken
    with pytest.raises(ConnectionError):
        pipeline.process_document(doc.id, db, storage, FakeExtractor())
    db.refresh(doc)
    assert doc.status == DocStatus.failed and "ConnectionError" in doc.error_message


def test_unreadable_image_fails(db, classified):
    doc = new_document(db)
    storage = FakeStorage({doc.file_key: b"%PDF-1.4 not an image"})
    assert pipeline.process_document(doc.id, db, storage, FakeExtractor()) == DocStatus.failed


def test_idempotent_unless_forced(db, classified):
    doc = new_document(db)
    extractor = FakeExtractor()
    run(db, doc, extractor)
    assert run(db, doc, extractor) == DocStatus.done
    assert len(extractions(db, doc)) == 1 and extractor.calls == ["khatian"]
    assert run(db, doc, extractor, force=True) == DocStatus.done
    assert len(extractions(db, doc)) == 2
    db.refresh(doc)
    assert doc.attempts == 2


def test_missing_document_returns_none(db):
    assert pipeline.process_document(uuid.uuid4(), db, FakeStorage({}), FakeExtractor()) is None


def test_make_extractor_rejects_unknown_name():
    assert pipeline.make_extractor("tesseract_regex").name == "tesseract_regex"
    with pytest.raises(ValueError):
        pipeline.make_extractor("magic")


def test_extractor_config_error_fails_the_document(db, monkeypatch):
    doc = new_document(db)

    def missing(name):
        raise ValueError("LLM settings missing: LLM_MODEL")

    monkeypatch.setattr(pipeline, "make_extractor", missing)
    assert pipeline.process_with_settings(doc.id, db, FakeStorage({}), "llm") == DocStatus.failed
    db.refresh(doc)
    assert "LLM_MODEL" in doc.error_message


def test_pipeline_sets_current_step_in_order(db, classified):
    doc = new_document(db)
    assert doc.current_step == DocStep.queued

    steps_seen = []
    original_commit = db.commit

    def tracking_commit():
        if doc.current_step not in steps_seen:
            steps_seen.append(doc.current_step)
        original_commit()

    db.commit = tracking_commit
    try:
        assert run(db, doc) == DocStatus.done
    finally:
        db.commit = original_commit

    assert steps_seen == [
        DocStep.reading,
        DocStep.classifying,
        DocStep.extracting,
        DocStep.normalizing,
        DocStep.finished,
    ]
