import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from conftest import TestSession

from app.api import documents as documents_api
from app.models import DocStatus, Document, Extraction, ExtractionStatus
from app.models.document import DocStep
from app.schemas.document import STATUS_LABELS_BN

PDF = ("deed.pdf", b"%PDF-1.4 fake", "application/pdf")


@pytest.fixture(autouse=True)
def enqueue(monkeypatch):
    """No real Celery: record the calls to process_document_task.delay."""
    delay = Mock()
    monkeypatch.setattr(documents_api.process_document_task, "delay", delay)
    return delay


def upload(client, file=PDF, doc_type="deed", **extra):
    data = {k: v for k, v in {"doc_type": doc_type, **extra}.items() if v is not None}
    return client.post("/documents", files={"file": file}, data=data)


def test_upload_success(client, storage):
    r = upload(client)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "uploaded"
    assert body["doc_type"] == "deed"
    assert body["original_filename"] == "deed.pdf"
    assert body["file_key"] == f"{body['id']}/deed.pdf"
    assert storage.objects[body["file_key"]] == (b"%PDF-1.4 fake", "application/pdf")


def test_upload_strips_path_from_filename(client):
    r = upload(client, file=("../../etc/passwd.pdf", b"x", "application/pdf"))
    assert r.status_code == 201
    assert r.json()["file_key"] == f"{r.json()['id']}/passwd.pdf"


def test_wrong_type_415(client, storage):
    r = upload(client, file=("a.txt", b"hello", "text/plain"))
    assert r.status_code == 415
    assert storage.objects == {}


def test_too_large_413(client, storage):
    big = b"0" * (10 * 1024 * 1024 + 1)
    r = upload(client, file=("big.pdf", big, "application/pdf"))
    assert r.status_code == 413
    assert storage.objects == {}


def test_unknown_land_404(client):
    assert upload(client, land_id=str(uuid.uuid4())).status_code == 404


def test_list_returns_uploaded_newest_first(client):
    first = upload(client).json()
    second = upload(client).json()
    ids = [d["id"] for d in client.get("/documents").json()["items"]]
    assert ids.index(second["id"]) < ids.index(first["id"])


def test_get_one_and_unknown_404(client):
    doc = upload(client).json()
    assert client.get(f"/documents/{doc['id']}").json()["id"] == doc["id"]
    assert client.get(f"/documents/{uuid.uuid4()}").status_code == 404


def test_upload_enqueues_once_after_commit(client, enqueue):
    def committed(doc_id, **kw):
        with TestSession() as other:  # a separate session sees only committed rows
            assert other.get(Document, uuid.UUID(doc_id)) is not None

    enqueue.side_effect = committed
    body = upload(client).json()
    enqueue.assert_called_once_with(body["id"])
    assert body["status"] == "uploaded" and body["attempts"] == 0
    assert body["detected_doc_type"] is None and body["label_warning"] is None


def test_upload_without_doc_type(client):
    r = upload(client, doc_type=None)
    assert r.status_code == 201, r.text
    assert r.json()["doc_type"] is None


def test_reprocess_enqueues_with_force(client, enqueue):
    doc = upload(client).json()
    enqueue.reset_mock()
    r = client.post(f"/documents/{doc['id']}/reprocess")
    assert r.status_code == 202
    enqueue.assert_called_once_with(doc["id"], force=True)
    assert client.post(f"/documents/{uuid.uuid4()}/reprocess").status_code == 404


def test_status_labels_for_status_and_step(client):
    for status in DocStatus:
        assert status.value in STATUS_LABELS_BN
        assert len(STATUS_LABELS_BN[status.value]) > 0
    for step in DocStep:
        assert step.value in STATUS_LABELS_BN
        assert len(STATUS_LABELS_BN[step.value]) > 0

    assert STATUS_LABELS_BN["uploaded"] == "আপলোড হয়েছে"
    assert STATUS_LABELS_BN["processing"] == "পড়া হচ্ছে"
    assert STATUS_LABELS_BN["done"] == "পড়া শেষ"
    assert STATUS_LABELS_BN["failed"] == "পড়া যায়নি"

    doc = upload(client).json()
    res = client.get(f"/documents/{doc['id']}").json()
    assert res["status_label_bn"] == "আপলোড হয়েছে"
    assert res["step_label_bn"] == STATUS_LABELS_BN["queued"]


def test_is_stale_threshold(client):
    doc_id = upload(client).json()["id"]
    with TestSession() as session:
        doc = session.get(Document, uuid.UUID(doc_id))
        doc.status = DocStatus.processing
        doc.updated_at = datetime.now(UTC) - timedelta(minutes=15)
        session.commit()

    res = client.get(f"/documents/{doc_id}").json()
    assert res["is_stale"] is True
    assert res["poll_after_s"] == 2

    with TestSession() as session:
        doc = session.get(Document, uuid.UUID(doc_id))
        doc.updated_at = datetime.now(UTC) - timedelta(minutes=2)
        session.commit()

    res = client.get(f"/documents/{doc_id}").json()
    assert res["is_stale"] is False

    with TestSession() as session:
        doc = session.get(Document, uuid.UUID(doc_id))
        doc.status = DocStatus.done
        doc.updated_at = datetime.now(UTC) - timedelta(minutes=20)
        session.commit()

    res = client.get(f"/documents/{doc_id}").json()
    assert res["is_stale"] is False
    assert res["poll_after_s"] is None


def test_latest_extraction_counts_needs_review(client):
    doc_id = upload(client).json()["id"]
    with TestSession() as session:
        doc = session.get(Document, uuid.UUID(doc_id))
        doc.status = DocStatus.done
        ex = Extraction(
            document_id=doc.id,
            extractor="fake",
            status=ExtractionStatus.needs_review,
            field_flags={
                "owners[0].name": ["low"],
                "plots[0].area_text": ["medium", "other_code"],
                "plots[1].dag_no": ["high"],
                "district": "low",
                "upazila": "high",
            },
            warnings=[
                {
                    "code": "unsupported_unit",
                    "field_path": "plots[0].area_text",
                    "message_bn": "একক",
                },
                {"code": "missing_unit", "field_path": "plots[1].area_text", "message_bn": "একক"},
            ],
        )
        session.add(ex)
        session.commit()

    res = client.get(f"/documents/{doc_id}").json()
    le = res["latest_extraction"]
    assert le is not None
    assert le["needs_review_count"] == 3
    assert le["warnings_count"] == 2


def test_extraction_endpoint_status_and_history(client):
    assert client.get(f"/documents/{uuid.uuid4()}/extraction").status_code == 404

    doc_id = upload(client).json()["id"]
    r = client.get(f"/documents/{doc_id}/extraction")
    assert r.status_code == 409
    assert "কাগজ পড়া এখনও শেষ হয়নি" in r.json()["detail"]

    with TestSession() as session:
        doc = session.get(Document, uuid.UUID(doc_id))
        doc.status = DocStatus.processing
        session.commit()

    r = client.get(f"/documents/{doc_id}/extraction")
    assert r.status_code == 409

    with TestSession() as session:
        doc = session.get(Document, uuid.UUID(doc_id))
        doc.status = DocStatus.done
        ex1 = Extraction(
            document_id=doc.id,
            extractor="fake1",
            status=ExtractionStatus.ok,
            data={
                "doc_type": "khatian",
                "khatian_no": "100",
                "district": "ঢাকা",
                "upazila": "সাভার",
                "mouza": "মৌজা",
                "plots": [],
                "owners": [],
            },
            cost_usd=0.02,
            latency_s=1.2,
            created_at=datetime.now(UTC) - timedelta(minutes=5),
        )
        ex2 = Extraction(
            document_id=doc.id,
            extractor="fake2",
            status=ExtractionStatus.needs_review,
            data={
                "doc_type": "khatian",
                "khatian_no": "101",
                "district": "ঢাকা",
                "upazila": "সাভার",
                "mouza": "মৌজা",
                "plots": [],
                "owners": [],
            },
            cost_usd=0.03,
            latency_s=1.5,
            created_at=datetime.now(UTC),
        )
        session.add_all([ex1, ex2])
        session.commit()

    r = client.get(f"/documents/{doc_id}/extraction")
    assert r.status_code == 200
    assert r.json()["extractor"] == "fake2"

    rh = client.get(f"/documents/{doc_id}/extraction?history=true")
    assert rh.status_code == 200
    items = rh.json()
    assert len(items) == 2
    assert items[0]["extractor"] == "fake2"
    assert items[1]["extractor"] == "fake1"


def test_cost_usd_never_appears_in_public_response(client):
    doc_id = upload(client).json()["id"]
    with TestSession() as session:
        doc = session.get(Document, uuid.UUID(doc_id))
        doc.status = DocStatus.done
        ex = Extraction(
            document_id=doc.id,
            extractor="fake",
            status=ExtractionStatus.ok,
            data={
                "doc_type": "khatian",
                "khatian_no": "100",
                "district": "ঢাকা",
                "upazila": "সাভার",
                "mouza": "মৌজা",
                "plots": [],
                "owners": [],
            },
            cost_usd=0.05,
            latency_s=2.5,
        )
        session.add(ex)
        session.commit()

    r_doc = client.get(f"/documents/{doc_id}")
    assert "cost_usd" not in r_doc.text
    assert "latency_s" not in r_doc.text

    r_ex = client.get(f"/documents/{doc_id}/extraction")
    assert "cost_usd" not in r_ex.text
    assert "latency_s" not in r_ex.text

    r_hist = client.get(f"/documents/{doc_id}/extraction?history=true")
    assert "cost_usd" not in r_hist.text
    assert "latency_s" not in r_hist.text


def test_list_filter_and_pagination(client):
    d1 = upload(client).json()
    d2 = upload(client).json()
    upload(client)  # a third document

    with TestSession() as session:
        doc1 = session.get(Document, uuid.UUID(d1["id"]))
        doc2 = session.get(Document, uuid.UUID(d2["id"]))
        doc1.status = DocStatus.done
        doc2.status = DocStatus.done
        session.commit()

    r_done = client.get("/documents?status=done")
    assert r_done.status_code == 200
    body = r_done.json()
    assert body["total"] >= 2
    assert all(d["status"] == "done" for d in body["items"])

    r_up = client.get("/documents?status=uploaded")
    assert r_up.status_code == 200
    assert all(d["status"] == "uploaded" for d in r_up.json()["items"])

    r_page = client.get("/documents?limit=2&offset=0")
    assert r_page.status_code == 200
    p_body = r_page.json()
    assert len(p_body["items"]) <= 2
    assert p_body["total"] >= 3
