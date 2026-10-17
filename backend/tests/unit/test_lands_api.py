import uuid

from conftest import TestSession

from app.models import DocStatus, DocType, Document, Land
from app.models.document import DocStep


def test_get_land(client):
    r = client.post("/lands", json={"mouza": "চাঁদশী", "dag_no": "305", "upazila": "গৌরনদী"})
    assert r.status_code == 201
    land_id = r.json()["id"]

    res = client.get(f"/lands/{land_id}")
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == land_id
    assert body["mouza"] == "চাঁদশী"
    assert body["dag_no"] == "305"
    assert body["upazila"] == "গৌরনদী"

    assert client.get(f"/lands/{uuid.uuid4()}").status_code == 404


def test_list_land_documents(client):
    r = client.post("/lands", json={"mouza": "চাঁদশী", "dag_no": "305"})
    assert r.status_code == 201
    land_id = uuid.UUID(r.json()["id"])

    # empty list
    r_empty = client.get(f"/lands/{land_id}/documents")
    assert r_empty.status_code == 200
    assert r_empty.json() == []

    # not found
    assert client.get(f"/lands/{uuid.uuid4()}/documents").status_code == 404

    # add documents to this land and another land
    with TestSession() as db:
        other_land = Land(mouza="অন্য", dag_no="১০০", district="", upazila="", khatian_no="")
        db.add(other_land)
        db.flush()

        doc1 = Document(
            id=uuid.uuid4(),
            land_id=land_id,
            doc_type=DocType.khatian,
            status=DocStatus.processing,
            current_step=DocStep.classifying,
            file_key="k1.png",
            original_filename="khatian.png",
        )
        doc2 = Document(
            id=uuid.uuid4(),
            land_id=land_id,
            doc_type=DocType.deed,
            status=DocStatus.done,
            current_step=DocStep.finished,
            file_key="d1.png",
            original_filename="deed.png",
            detected_doc_type=DocType.deed,
        )
        doc_other = Document(
            id=uuid.uuid4(),
            land_id=other_land.id,
            doc_type=DocType.khatian,
            status=DocStatus.done,
            current_step=DocStep.finished,
            file_key="k2.png",
            original_filename="other.png",
        )
        db.add_all([doc1, doc2, doc_other])
        db.commit()

    res = client.get(f"/lands/{land_id}/documents")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 2
    assert items[0]["id"] == str(doc1.id)
    assert items[0]["original_filename"] == "khatian.png"
    assert items[0]["status"] == "processing"
    assert items[0]["current_step"] == "classifying"
    assert items[1]["id"] == str(doc2.id)
    assert items[1]["original_filename"] == "deed.png"
    assert items[1]["status"] == "done"
