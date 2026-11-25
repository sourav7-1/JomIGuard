"""Extraction must survive provider failures: retry with backoff, then fall back
(GEMINI_FALLBACK_MODEL -> other provider -> Tesseract), else a friendly "পড়া যায়নি" that a
retry can fix. Every provider is mocked; no network."""

import uuid
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import cv2
import httpx
import numpy as np
import pytest
from conftest import TestSession
from google.genai import errors
from pydantic import SecretStr
from sqlalchemy import select
from test_gemini_extractor import FakeClient, answer, response
from test_pipeline import PNG, FakeExtractor, FakeStorage

from app.api import documents as documents_api
from app.core.config import settings
from app.models import DocStatus, Document, Extraction, ExtractionStatus, Land
from app.models.document import DocStep
from app.services import pipeline
from app.services.classify import ClassifyResult
from app.services.extraction import Budget, ExtractionMeta, ExtractionResult
from app.services.extraction import gemini as gm
from app.services.extraction.fallback import TESSERACT, FallbackExtractor, make_fallback_extractor
from app.services.journey import build_journey, incomplete_reasons, journey_input
from app.services.land_case import load_land_case


def lined_page() -> bytes:
    page = np.full((900, 700), 255, np.uint8)
    for y in range(80, 800, 40):
        cv2.line(page, (60, y), (640, y), 0, 3)
    return cv2.imencode(".png", page)[1].tobytes()


PNG_PAGE = lined_page()  # the mocked provider decides the answer


def unavailable(retry_after: str | None = None):
    headers = {"retry-after": retry_after} if retry_after else {}
    return errors.ServerError(
        503,
        {"error": {"code": 503, "message": "overloaded", "status": "UNAVAILABLE"}},
        SimpleNamespace(headers=headers),
    )


@pytest.fixture(autouse=True)
def waits(monkeypatch):
    slept = []
    monkeypatch.setattr(gm, "sleep", slept.append)
    return slept


@pytest.fixture
def classified(monkeypatch):
    monkeypatch.setattr(pipeline, "classify_ocr", lambda read: ClassifyResult("khatian", 0.9))


def gemini(tmp_path, client, model="gemini-main"):
    return gm.GeminiExtractor(
        client=client,
        model=model,
        price_input_per_mtok=Decimal(0),
        price_output_per_mtok=Decimal(0),
        cache_dir=tmp_path / model,
        budget=Budget(tmp_path / "spend.json", Decimal("1"), today=lambda: date(2026, 11, 25)),
    )


def failing(error="api: ServerError 503"):
    return FakeExtractor(ExtractionResult(error=error, meta=ExtractionMeta(model="x")))


# --- 1. retry with backoff ---


def test_503_then_success_retries_with_backoff(tmp_path, waits):
    client = FakeClient(unavailable(), response(answer()))
    result = gemini(tmp_path, client).extract(PNG_PAGE, "khatian")
    assert result.document is not None and len(client.calls) == 2
    assert waits == [gm.BACKOFF_S]


def test_retry_after_is_honoured_and_capped(tmp_path, waits):
    client = FakeClient(unavailable("12"), unavailable("600"), response(answer()))
    assert gemini(tmp_path, client).extract(PNG_PAGE, "khatian").document is not None
    assert waits == [12.0, gm.MAX_BACKOFF_S]  # 12 s > 4 s backoff; 600 s cut to the cap


def test_timeout_and_500_are_retried(tmp_path, waits):
    server_error = errors.ServerError(500, {"error": {"code": 500, "message": "x"}})
    client = FakeClient(httpx.ReadTimeout("slow"), server_error, response(answer()))
    assert gemini(tmp_path, client).extract(PNG_PAGE, "khatian").document is not None
    assert len(client.calls) == 3 and len(waits) == 2


def test_default_is_three_tries_in_about_twenty_seconds(tmp_path, waits):
    client = FakeClient(unavailable())
    result = gemini(tmp_path, client).extract(PNG_PAGE, "khatian")
    assert result.error == "api: ServerError 503" and len(client.calls) == 3
    assert sum(waits) <= 20


# --- 2. fallback chain ---


def test_503_always_falls_back_to_the_fallback_model(tmp_path):
    main, spare = FakeClient(unavailable()), FakeClient(response(answer()))
    chain = FallbackExtractor([
        ("gemini", lambda: gemini(tmp_path, main)),
        ("gemini:spare", lambda: gemini(tmp_path, spare, model="gemini-spare")),
        (TESSERACT, lambda: pytest.fail("Tesseract must not run when a model answered")),
    ])  # fmt: skip
    result = chain.extract(PNG_PAGE, "khatian")
    assert result.document is not None and result.extractor == "gemini:spare"
    assert len(main.calls) == 3 and len(spare.calls) == 1
    assert spare.calls[0]["model"] == "gemini-spare"


def test_chain_order_comes_from_the_settings(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_model", "gemini-main")
    monkeypatch.setattr(settings, "gemini_api_key", SecretStr("test-key"))
    monkeypatch.setattr(settings, "anthropic_api_key", SecretStr("test-key"))
    monkeypatch.setattr(settings, "gemini_fallback_model", "gemini-spare")
    names = [name for name, _ in make_fallback_extractor().steps]
    assert names == ["gemini", "gemini:gemini-spare", "anthropic", TESSERACT]

    monkeypatch.setattr(settings, "gemini_fallback_model", "")
    monkeypatch.setattr(settings, "anthropic_api_key", None)
    assert [n for n, _ in make_fallback_extractor().steps] == ["gemini", TESSERACT]

    monkeypatch.setattr(settings, "llm_provider", "anthropic")
    assert [n for n, _ in make_fallback_extractor().steps] == ["anthropic", "gemini", TESSERACT]


def test_a_step_that_cannot_be_built_or_crashes_is_skipped():
    def not_configured():
        raise ValueError("LLM settings missing: LLM_MODEL")

    chain = FallbackExtractor([
        ("anthropic", not_configured),
        ("gemini", lambda: FakeExtractor(raises=RuntimeError("sdk bug"))),
        (TESSERACT, FakeExtractor),
    ])  # fmt: skip
    assert chain.extract(PNG, "khatian").extractor == TESSERACT


def run_chain(db, chain, doc=None):
    doc = doc or Document(id=uuid.uuid4(), file_key="k/k.png", original_filename="k.png")
    db.add(doc)
    db.commit()
    storage = FakeStorage({doc.file_key: PNG})
    return doc, pipeline.process_document(doc.id, db, storage, chain, force=True)


def test_all_providers_fail_then_tesseract_reads_a_limited_document(classified):
    tesseract = FakeExtractor()
    chain = FallbackExtractor([
        ("gemini", failing), ("gemini:spare", failing), ("anthropic", failing),
        (TESSERACT, lambda: tesseract),
    ])  # fmt: skip
    with TestSession() as db:
        land = Land(district="ঢাকা", upazila="সাভার", mouza="নমুনা", dag_no="১", khatian_no="১")
        db.add(land)
        db.commit()
        doc = Document(id=uuid.uuid4(), land_id=land.id, file_key="k/k.png",
                       original_filename="k.png")  # fmt: skip
        doc, status = run_chain(db, chain, doc)
        assert status == DocStatus.done and tesseract.calls == ["khatian"]
        row = db.scalars(select(Extraction).where(Extraction.document_id == doc.id)).one()
        # limited read: marked, every field needs review, and the case shows it as a gap
        assert row.extractor == TESSERACT and row.status == ExtractionStatus.needs_review
        assert all("high" not in f for f in row.field_flags.values())
        # the rules see it as an OCR read, so its numbers never make a mismatch
        assert [d.ocr_read for d in load_land_case(db, land.id).documents] == [True]
        reasons = incomplete_reasons(journey_input(db, land, None))
        assert any("সীমিত পাঠে (OCR)" in r for r in reasons)
        journey = build_journey(journey_input(db, land, None))
        assert journey.steps[1].status == "done"  # the rules can run on it (step 3 opens)


# --- 3. everything fails: friendly message, and a retry that works ---


def test_everything_fails_then_retry_reads_it(classified, client, monkeypatch, caplog):
    enqueue = Mock()
    monkeypatch.setattr(documents_api.process_document_task, "delay", enqueue)
    chain = FallbackExtractor([("gemini", failing), (TESSERACT, lambda: failing("ocr: no text"))])
    with TestSession() as db:
        doc, status = run_chain(db, chain)
        db.refresh(doc)
        assert status == DocStatus.failed
        assert doc.error_message == pipeline.EXTRACT_FAILED_BN  # friendly Bangla only
        assert "503" not in doc.error_message and "ocr: no text" in caplog.text

    r = client.post(f"/documents/{doc.id}/reprocess")  # the "আবার চেষ্টা" button
    assert r.status_code == 202, r.text
    enqueue.assert_called_once_with(str(doc.id), force=True)
    with TestSession() as db:
        queued = db.get(Document, doc.id)
        assert queued.status == DocStatus.processing and queued.current_step == DocStep.queued
        assert queued.error_message is None  # no longer shown as failed while it waits
        # the worker runs again, the provider is back
        _, status = run_chain(db, FallbackExtractor([("gemini", FakeExtractor)]), queued)
        assert status == DocStatus.done
