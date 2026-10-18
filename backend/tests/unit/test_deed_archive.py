import uuid
from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from conftest import TEST_ADMIN_ID, TestSession
from sqlalchemy import func, select

from app.api import documents as documents_api
from app.models import DocStatus, Document, Extraction, ExtractionStatus, Land, User
from app.scripts.demo_reset import seed_historical_deeds
from app.services.deed_archive import compare_deeds, integrity_status
from app.services.land_case import load_land_case
from app.services.risk import assess
from app.services.rules import run_rules
from app.services.timeline import build_timeline


@pytest.fixture(autouse=True)
def no_worker(monkeypatch):
    monkeypatch.setattr(documents_api.process_document_task, "delay", Mock())


def _deed(number: str, year: str, seller: str, buyer: str) -> dict:
    return {
        "doc_type": "deed",
        "deed_type": "saf_kabala",
        "is_draft": False,
        "deed_no": number,
        "deed_year": year,
        "registration_date": f"{year}-06-15",
        "registration_date_text": f"15/06/{year}",
        "sellers": [{"name": seller}],
        "buyers": [{"name": buyer}],
        "schedule_location": {"district": "নমুনা", "upazila": "নমুনা", "mouza": "নমুনা"},
        "schedule_khatians": [],
        "schedule_plots": [{"dag_no": "305", "area_text": "২ শতাংশ"}],
        "transferred_area_text": "২ শতাংশ",
    }


def test_deed_archive_lists_source_fields_and_compares_same_land(client):
    land = client.post("/lands", json={"mouza": "নমুনা", "dag_no": "305"}).json()
    ids = []
    for deed in (_deed("10", "2001", "এক", "দুই"), _deed("20", "2010", "দুই", "তিন")):
        upload = client.post(
            "/documents",
            files={"file": ("synthetic.pdf", b"synthetic deed", "application/pdf")},
            data={"doc_type": "deed", "land_id": land["id"]},
        )
        assert upload.status_code == 201
        document_id = uuid.UUID(upload.json()["id"])
        ids.append(document_id)
        with TestSession() as db:
            doc = db.get(Document, document_id)
            doc.status = DocStatus.done
            db.add(
                Extraction(
                    document_id=document_id,
                    extractor="seed",
                    status=ExtractionStatus.ok,
                    data=deed,
                    created_at=datetime.now(UTC),
                )
            )
            db.commit()

    result = client.get(f"/lands/{land['id']}/deeds")
    assert result.status_code == 200, result.text
    body = result.json()
    assert [item["id"] for item in body["items"]] == [str(item) for item in ids]
    assert body["items"][1]["previous_document_id"] == str(ids[0])
    assert body["items"][1]["comparison"][0]["previous"] == "10"
    assert body["items"][1]["comparison"][0]["current"] == "20"
    assert body["official_source_verified"] is False
    assert "সরকারি উৎসে" in body["notice_bn"]


def test_fingerprint_verification_reports_unchanged_and_changed_bytes(client, storage):
    response = client.post(
        "/documents", files={"file": ("synthetic.pdf", b"first bytes", "application/pdf")}
    )
    document_id = response.json()["id"]
    unchanged = client.post(f"/documents/{document_id}/fingerprint/verify").json()
    assert unchanged["unchanged_since_upload"] is True
    assert unchanged["current_sha256"] == unchanged["stored_sha256"]
    assert unchanged["official_source_verified"] is False

    with TestSession() as db:
        doc = db.get(Document, uuid.UUID(document_id))
        storage.objects[doc.file_key] = (b"changed bytes", "application/pdf")
    changed = client.post(f"/documents/{document_id}/fingerprint/verify").json()
    assert changed["unchanged_since_upload"] is False
    assert changed["current_sha256"] != changed["stored_sha256"]


def test_fingerprint_for_legacy_record_does_not_claim_unchanged(client, storage):
    response = client.post(
        "/documents", files={"file": ("synthetic.pdf", b"legacy", "application/pdf")}
    )
    with TestSession() as db:
        doc = db.get(Document, uuid.UUID(response.json()["id"]))
        doc.content_sha256 = None
        db.commit()
    result = client.post(f"/documents/{response.json()['id']}/fingerprint/verify").json()
    assert result["stored_sha256"] is None
    assert result["unchanged_since_upload"] is None


def test_other_users_cannot_list_land_deeds(client):
    with TestSession() as db:
        other = User(username="other-deed-user", password_hash="unused")
        db.add(other)
        db.flush()
        land = Land(
            owner_id=other.id,
            district="",
            upazila="",
            mouza="নমুনা",
            dag_no="1",
            khatian_no="",
        )
        db.add(land)
        db.commit()
        land_id = land.id
    assert client.get(f"/lands/{land_id}/deeds").status_code == 404


def test_demo_historical_deeds_seed_is_idempotent_and_keeps_rows(storage):
    land_id = uuid.uuid4()
    with TestSession() as db:
        db.add(
            Land(
                id=land_id,
                owner_id=TEST_ADMIN_ID,
                district="",
                upazila="",
                mouza="নমুনা",
                dag_no="2484",
                khatian_no="",
            )
        )
        db.commit()
        seed_historical_deeds(db, storage, land_id)
        deed_docs = select(func.count()).select_from(Document).where(Document.land_id == land_id)
        first_count = db.scalar(deed_docs)
        seed_historical_deeds(db, storage, land_id)
        second_count = db.scalar(deed_docs)
        assert first_count == second_count == 2
        extractions = (
            select(func.count())
            .select_from(Extraction)
            .join(Document)
            .where(Document.land_id == land_id)
        )
        assert db.scalar(extractions) == 2
        case = load_land_case(db, land_id)
        timeline = build_timeline(case, assess(case, run_rules(case)))
        assert [event["year"] for event in timeline["events"]] == [1992, 2003]
        assert [event["kind"] for event in timeline["events"]] == ["sale", "proposed_sale"]


def test_deed_comparison_uses_only_printed_fields():
    fields = compare_deeds(_deed("2", "2010", "B", "C"), _deed("1", "2001", "A", "B"))
    assert fields[0]["current"] == "2" and fields[0]["previous"] == "1"
    assert fields[3]["current"] == ["B"] and fields[3]["previous"] == ["A"]
    assert fields[-1]["current"] == "২ শতাংশ"


def test_deed_integrity_status_handles_missing_and_changed_stored_bytes():
    import hashlib
    from types import SimpleNamespace

    original = b"original"
    document = SimpleNamespace(content_sha256=hashlib.sha256(original).hexdigest(), file_key="copy")
    assert integrity_status(document, Mock(download=Mock(return_value=original))) == "কপি অপরিবর্তিত"
    assert integrity_status(document, Mock(download=Mock(return_value=b"changed"))) == "কপি বদলেছে"
    assert integrity_status(document, Mock(download=Mock(side_effect=KeyError))) == "ফাইল পাওয়া যায়নি"


def test_missing_file_is_reported_even_without_a_saved_fingerprint():
    document = Mock(content_sha256=None, file_key="missing")
    assert integrity_status(document, Mock(download=Mock(side_effect=KeyError))) == "ফাইল পাওয়া যায়নি"


def test_provenance_audit_is_append_only_through_api(client):
    from app.models import DocumentAuditEvent

    land = client.post("/lands", json={"mouza": "নমুনা", "dag_no": "305"}).json()
    doc = client.post(
        "/documents",
        files={"file": ("synthetic.pdf", b"vault bytes", "application/pdf")},
        data={"doc_type": "deed", "land_id": land["id"]},
    ).json()
    changed = client.patch(
        f"/documents/{doc['id']}/provenance", json={"source_type": "certified_copy_user_claim"}
    )
    assert changed.status_code == 200 and changed.json()["official_source_verified"] is False
    with TestSession() as db:
        events = db.scalars(
            select(DocumentAuditEvent)
            .where(DocumentAuditEvent.document_id == uuid.UUID(doc["id"]))
            .order_by(DocumentAuditEvent.created_at, DocumentAuditEvent.id)
        ).all()
        assert [event.event for event in events] == ["uploaded", "provenance_changed"]
        assert all(event.actor == str(TEST_ADMIN_ID) for event in events)


def test_deed_compare_endpoint_checks_chain_dag_area_and_owner_scope(client):
    land = client.post("/lands", json={"mouza": "নমুনা", "dag_no": "305"}).json()
    ids = []
    seller = "মোঃ করিম উদ্দিন"
    for number, year, deed_seller, deed_buyer in (
        ("1", "2001", "আব্দুল কাদের", seller),
        ("2", "2010", seller, "নাসির উদ্দিন"),
    ):
        response = client.post(
            "/documents",
            files={"file": ("synthetic.pdf", b"same", "application/pdf")},
            data={"doc_type": "deed", "land_id": land["id"]},
        )
        ids.append(response.json()["id"])
        data = _deed(number, year, deed_seller, deed_buyer)
        data["transferred_area_shatangsho"] = "2" if number == "1" else "1.5"
        with TestSession() as db:
            doc = db.get(Document, uuid.UUID(response.json()["id"]))
            doc.status = DocStatus.done
            db.add(
                Extraction(
                    document_id=doc.id,
                    extractor="seed",
                    created_by="seed",
                    status=ExtractionStatus.ok,
                    data=data,
                )
            )
            db.commit()
    body = client.get(
        f"/lands/{land['id']}/deeds/compare", params={"a": ids[1], "b": ids[0]}
    ).json()
    assert body["links"] == {"buyer_to_seller": True, "same_dag": True, "area_within": True}
    assert body["official_source_verified"] is False


def test_deed_claim_words_are_allowed_only_in_fixed_disclaimer():
    from app.services.risk import DEED_DISCLAIMER_BN, forbidden_words_in

    assert forbidden_words_in(DEED_DISCLAIMER_BN) == []
    for claim in ("authentic", "genuine", "fake"):
        assert forbidden_words_in(f"This deed is {claim}")
    bangla_claims = (
        "".join(map(chr, (0x0986, 0x09B8, 0x09B2, 0x0020, 0x09A6, 0x09B2, 0x09BF, 0x09B2))),
        "".join(map(chr, (0x099C, 0x09BE, 0x09B2, 0x0020, 0x09A6, 0x09B2, 0x09BF, 0x09B2))),
    )
    for claim in bangla_claims:
        assert forbidden_words_in(f"?? deed {claim}")


def test_demo_00001_seeds_1985_deed(storage):
    land_id = uuid.uuid4()
    with TestSession() as db:
        db.add(
            Land(
                id=land_id,
                owner_id=TEST_ADMIN_ID,
                district="",
                upazila="",
                mouza="",
                dag_no="",
                khatian_no="",
            )
        )
        db.commit()
        seed_historical_deeds(db, storage, land_id, "00001")
        rows = db.scalars(select(Document).where(Document.land_id == land_id)).all()
        assert len(rows) == 1
        extraction = db.scalar(select(Extraction).where(Extraction.document_id == rows[0].id))
        assert extraction.created_by == "seed" and extraction.data["deed_year"] == "1985"
