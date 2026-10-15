import uuid
from unittest.mock import Mock

import pytest
from conftest import TestSession

from app.api import documents as documents_api
from app.models import Document

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
    ids = [d["id"] for d in client.get("/documents").json()]
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
