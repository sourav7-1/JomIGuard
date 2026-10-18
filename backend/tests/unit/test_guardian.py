import hashlib
import uuid

from conftest import TEST_ADMIN_ID, TestSession
from sqlalchemy import delete, select

from app.models import (
    DocStatus,
    DocType,
    Document,
    Extraction,
    ExtractionStatus,
    GuardedLand,
    IdentityVerification,
    User,
)
from app.scripts.guardian_seed import _uid, seed_guardian
from app.services.deed_archive import integrity_status
from app.services.guardian import diff_khatians


def khatian(owner="নাসির উদ্দিন", **changes):
    data = {
        "owners": [{"name": owner, "share_text": "১.০০০", "share_fraction": "1.000"}],
        "total_area_text": "১.০০০",
        "khatian_no": "১২",
        "mutation_case_ref": None,
        "annual_revenue_text": "১০ টাকা",
        "location": {"district": "বরিশাল", "upazila": "সদর", "mouza": "ডেমো"},
        "plots": [{"dag_no": "১০২"}],
    }
    data.update(changes)
    return data


def test_diff_owner_area_share_mutation_khatian_holding_and_confidence():
    old = khatian()
    assert diff_khatians(old, khatian(owner="মোঃ জলিল"))["severity"] == "bad"
    changed_share = khatian()
    changed_share["owners"][0]["share_text"] = ".৫০০"
    assert diff_khatians(old, changed_share)["severity"] == "bad"
    assert diff_khatians(old, khatian(total_area_text="২.০০০"))["severity"] == "bad"
    assert diff_khatians(old, khatian(mutation_case_ref="১২৪৩/২৬"))["severity"] == "warn"
    assert diff_khatians(old, khatian(khatian_no="১৩"))["severity"] == "warn"
    assert diff_khatians(old, khatian(annual_revenue_text="২০ টাকা"))["severity"] == "info"
    assert (
        diff_khatians(
            old, khatian(total_area_text="২.০০০"), low_confidence_fields=("total_area_text",)
        )["severity"]
        == "warn"
    )


def test_spelling_variation_and_same_owner_revenue_do_not_create_owner_alert():
    result = diff_khatians(khatian("ইউসুফ মিযা"), khatian("ইউসুফ মিয়া"))
    assert result["changes"] == []


def test_verified_user_removed_message_and_no_new_owner_case():
    result = diff_khatians(khatian(), khatian("মোঃ জলিল"), user_verified_name="নাসির উদ্দিন")
    assert any("নতুন খতিয়ানে আপনার নাম নেই" in change["message_bn"] for change in result["changes"])


def test_guardian_api_creates_snapshots_alert_and_limits_to_own_lands(client):
    doc_id = uuid.uuid4()
    with TestSession() as db:
        doc = Document(
            id=doc_id,
            owner_id=TEST_ADMIN_ID,
            doc_type=DocType.khatian,
            detected_doc_type=DocType.khatian,
            status=DocStatus.done,
            file_key="guardian/old.png",
            original_filename="old.png",
        )
        db.add(doc)
        db.flush()
        extraction = Extraction(
            document_id=doc.id,
            extractor="seed",
            status=ExtractionStatus.ok,
            data=khatian(),
            warnings=[],
            field_flags={},
        )
        db.add(extraction)
        other = User(username="other-guardian", password_hash="not-a-real-password-hash")
        db.add(other)
        db.flush()
        db.add(
            GuardedLand(
                user_id=other.id,
                label_bn="অন্যের জমি",
                district="বরিশাল",
                upazila="সদর",
                mouza="ডেমো",
                dag_no="৯৯৯",
                khatian_no="১",
            )
        )
        db.commit()
    created = client.post("/guardian/lands", json={"document_id": str(doc_id)})
    assert created.status_code == 201, created.text
    land_id = created.json()["id"]
    assert len(client.get("/guardian/lands").json()) == 1
    new_doc_id = uuid.uuid4()
    with TestSession() as db:
        doc = Document(
            id=new_doc_id,
            owner_id=TEST_ADMIN_ID,
            doc_type=DocType.khatian,
            detected_doc_type=DocType.khatian,
            status=DocStatus.done,
            file_key="guardian/new.png",
            original_filename="new.png",
        )
        db.add(doc)
        db.flush()
        data = khatian(owner="মোঃ জলিল", mutation_case_ref="১২৪৩/২৬")
        db.add(
            Extraction(
                document_id=doc.id,
                extractor="seed",
                status=ExtractionStatus.ok,
                data=data,
                warnings=[],
                field_flags={},
            )
        )
        db.commit()
    checked = client.post(f"/guardian/lands/{land_id}/check", json={"document_id": str(new_doc_id)})
    assert checked.status_code == 200 and checked.json()["severity"] == "bad"
    alerts = client.get(f"/guardian/lands/{land_id}/alerts").json()
    assert len(alerts) == 1 and alerts[0]["old"]["owners"][0]["name"] == "নাসির উদ্দিন"
    assert client.get(f"/guardian/lands/{uuid.uuid4()}/alerts").status_code == 404


def test_guardian_demo_seed_repairs_missing_objects_and_is_idempotent(monkeypatch, storage, client):
    monkeypatch.setattr("app.scripts.guardian_seed.get_storage", lambda: storage)
    monkeypatch.setattr("app.api.guardian.get_storage", lambda: storage)
    with TestSession() as db:
        seed_guardian(db)
        seeded_docs = db.scalars(
            select(Document).where(
                Document.original_filename.like("guardian-base-%")
                | Document.original_filename.like("guardian-demo-%")
            )
        ).all()
        assert len(seeded_docs) == 7
        legacy_ids = []
        for index, source in enumerate(seeded_docs):
            legacy_id = uuid.uuid4()
            legacy_ids.append(legacy_id)
            legacy = Document(
                id=legacy_id,
                owner_id=TEST_ADMIN_ID,
                doc_type=DocType.khatian,
                detected_doc_type=DocType.khatian,
                status=DocStatus.done,
                file_key=f"guardian/legacy/{legacy_id}.json",
                original_filename=f"guardian-demo-baseline-{index}.json",
            )
            db.add(legacy)
            db.flush()
            source_extraction = db.scalar(
                select(Extraction).where(Extraction.document_id == source.id)
            )
            db.add(
                Extraction(
                    document_id=legacy.id,
                    extractor="seed",
                    created_by="seed",
                    status=ExtractionStatus.ok,
                    data=source_extraction.data,
                    warnings=[],
                    field_flags={},
                )
            )
        db.commit()
        for doc in seeded_docs:
            storage.objects.pop(doc.file_key)
            doc.file_key = f"missing/{doc.id}"
            doc.original_filename = f"legacy-{doc.id}.json"
            doc.content_sha256 = None
        db.commit()

        seed_guardian(db)
        seed_guardian(db)
        for legacy_id in legacy_ids:
            legacy = db.get(Document, legacy_id)
            content = storage.download(legacy.file_key)
            assert legacy.content_sha256 == hashlib.sha256(content).hexdigest()
            assert integrity_status(legacy, storage) == (
                "\u0995\u09aa\u09bf \u0985\u09aa\u09b0\u09bf\u09ac\u09b0\u09cd\u09a4\u09bf\u09a4"
            )
        ids = [_uid(f"guardian-land-{dag}") for dag in ("১০২", "১০৮", "২২১", "৩০৫", "৪১০")]
        rows = db.scalars(select(GuardedLand).where(GuardedLand.id.in_(ids))).all()
        buyer = db.query(IdentityVerification).filter_by(provider_ref="guardian-demo-buyer").all()
        assert len(rows) == 5
        assert {row.dag_no for row in rows} == {"১০২", "১০৮", "২২১", "৩০৫", "৪১০"}
        assert len(buyer) == 1 and buyer[0].name_bn_as_per_nid == "নাসির উদ্দিন"
        for doc in db.scalars(
            select(Document).where(
                Document.original_filename.like("guardian-base-%")
                | Document.original_filename.like("guardian-demo-%")
            )
        ):
            content = storage.download(doc.file_key)
            assert doc.content_sha256 == hashlib.sha256(content).hexdigest()
            assert integrity_status(doc, storage) == "কপি অপরিবর্তিত"
        listed = client.get("/guardian/lands")
        assert listed.status_code == 200
        listed_docs = [doc for land in listed.json() for doc in land["documents"]]
        expected_doc_ids = {
            str(_uid(f"guardian-base-doc-{dag}")) for dag in ("১০২", "১০৮", "২২১", "৩০৫", "৪১০")
        } | {str(_uid(f"guardian-new-doc-{dag}")) for dag in ("২২১", "৩০৫")}
        listed_demo_docs = [doc for doc in listed_docs if doc["id"] in expected_doc_ids]
        assert len(listed_demo_docs) == 7
        assert {doc["integrity"] for doc in listed_demo_docs} == {"কপি অপরিবর্তিত"}
        db.execute(delete(GuardedLand).where(GuardedLand.id.in_(ids)))
        db.execute(
            delete(IdentityVerification).where(
                IdentityVerification.provider_ref == "guardian-demo-buyer"
            )
        )
        db.execute(delete(Document).where(Document.original_filename.like("guardian-base-%")))
        db.execute(delete(Document).where(Document.original_filename.like("guardian-demo-%")))
        db.execute(delete(Document).where(Document.id.in_(legacy_ids)))
        db.commit()
