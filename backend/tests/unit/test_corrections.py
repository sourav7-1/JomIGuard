import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from conftest import TestSession

from app.models import DocStatus, Document, Extraction, ExtractionStatus, Land


def _create_sample_land_and_doc(session):
    land = Land(
        district="ঢাকা",
        upazila="সাভার",
        mouza="ভাটারা",
        dag_no="305",
        khatian_no="882",
    )
    session.add(land)
    session.flush()

    doc = Document(
        id=uuid.uuid4(),
        land_id=land.id,
        doc_type="khatian",
        file_key="test/khatian.jpg",
        original_filename="khatian.jpg",
        status=DocStatus.done,
    )
    session.add(doc)
    session.flush()

    data = {
        "doc_type": "khatian",
        "survey_type": "BS",
        "location": {
            "district": "ঢাকা",
            "upazila": "সাভার",
            "mouza": "ভাটারা",
            "jl_no": "45",
        },
        "khatian_no": "882",
        "touzi_no": "100",
        "owners": [
            {
                "name": "মোঃ রহিম উদ্দিন",
                "name_normalized": "রহিম উদ্দিন",
                "father_or_husband_name": "রহমান",
                "relation_marker": "father",
                "address_text": "সাং ভাটারা",
                "share_text": ".৪০০",
                "share_fraction": "0.4",
                "share_shatangsho": "6.0",
            },
            {
                "name": "করিম উদ্দিন",
                "name_normalized": "করিম উদ্দিন",
                "father_or_husband_name": "রহমান",
                "relation_marker": "father",
                "address_text": "সাং ভাটারা",
                "share_text": ".৬০০",
                "share_fraction": "0.6",
                "share_shatangsho": "9.0",
            },
        ],
        "plots": [
            {
                "dag_no": "305",
                "land_class": "নাল",
                "area_text": "১৫ শতাংশ",
                "area_shatangsho": "15.0",
            }
        ],
        "area_unit_text": "শতাংশ",
        "total_area_text": "১৫ শতাংশ",
        "total_area_shatangsho": "15.0",
    }

    ex = Extraction(
        document_id=doc.id,
        extractor="tesseract_regex",
        status=ExtractionStatus.ok,
        data=data,
        field_flags={"owners[0].share_text": ["low"]},
        created_at=datetime.now(UTC) - timedelta(minutes=5),
    )
    session.add(ex)
    session.commit()
    return land, doc, ex


def test_correction_creates_new_extraction_and_keeps_old(client):
    with TestSession() as session:
        land, doc, old_ex = _create_sample_land_and_doc(session)
        doc_id = str(doc.id)

    r = client.patch(
        f"/documents/{doc_id}/extraction",
        json={"edits": [{"field_path": "khatian_no", "value": "883"}]},
    )
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["extractor"] == "human"
    assert res["status"] == "ok"
    assert res["data"]["khatian_no"] == "883"

    # History contains both
    rh = client.get(f"/documents/{doc_id}/extraction?history=true")
    assert rh.status_code == 200
    items = rh.json()
    assert len(items) == 2
    assert items[0]["extractor"] == "human"
    assert items[0]["data"]["khatian_no"] == "883"
    assert items[1]["extractor"] == "tesseract_regex"
    assert items[1]["data"]["khatian_no"] == "882"


def test_editing_share_text_recomputes_share_shatangsho(client):
    with TestSession() as session:
        land, doc, _ = _create_sample_land_and_doc(session)
        doc_id = str(doc.id)

    r = client.patch(
        f"/documents/{doc_id}/extraction",
        json={"edits": [{"field_path": "owners[0].share_text", "value": ".৫০০"}]},
    )
    assert r.status_code == 200
    res = r.json()
    assert Decimal(str(res["data"]["owners"][0]["share_fraction"])) == Decimal("0.5")
    # 0.5 * 15.0 total = 7.5
    assert Decimal(str(res["data"]["owners"][0]["share_shatangsho"])) == Decimal("7.5")


def test_editing_derived_field_is_rejected(client):
    with TestSession() as session:
        land, doc, _ = _create_sample_land_and_doc(session)
        doc_id = str(doc.id)

    r = client.patch(
        f"/documents/{doc_id}/extraction",
        json={"edits": [{"field_path": "owners[0].share_shatangsho", "value": "10.0"}]},
    )
    assert r.status_code == 400
    assert "স্বয়ংক্রিয়ভাবে" in r.text or "বদলানো যায় না" in r.text


def test_invalid_identifier_422(client):
    with TestSession() as session:
        land, doc, _ = _create_sample_land_and_doc(session)
        doc_id = str(doc.id)

    # Int instead of string
    r = client.patch(
        f"/documents/{doc_id}/extraction",
        json={"edits": [{"field_path": "khatian_no", "value": 123}]},
    )
    assert r.status_code == 422
    assert "khatian_no" in r.text


def test_confirm_sets_confidence_human(client):
    with TestSession() as session:
        land, doc, _ = _create_sample_land_and_doc(session)
        doc_id = str(doc.id)

    r = client.patch(
        f"/documents/{doc_id}/extraction",
        json={"confirms": ["owners[0].share_text"]},
    )
    assert r.status_code == 200
    res = r.json()
    assert res["field_flags"]["owners[0].share_text"] == ["human"]


def test_removing_and_adding_owner_row(client):
    with TestSession() as session:
        land, doc, _ = _create_sample_land_and_doc(session)
        doc_id = str(doc.id)

    r = client.patch(
        f"/documents/{doc_id}/extraction",
        json={
            "edits": [
                {"field_path": "owners[1]", "remove": True},
                {
                    "field_path": "owners[+]",
                    "value": {
                        "name": "নতুন মালিক",
                        "father_or_husband_name": "পিতা",
                        "relation_marker": "father",
                        "address_text": "ঢাকা",
                        "share_text": ".১০০",
                    },
                },
            ]
        },
    )
    assert r.status_code == 200
    res = r.json()
    owners = res["data"]["owners"]
    assert len(owners) == 2
    assert owners[0]["name"] == "মোঃ রহিম উদ্দিন"
    assert owners[1]["name"] == "নতুন মালিক"
    assert Decimal(str(owners[1]["share_shatangsho"])) == Decimal("1.5")


def test_case_view_reports_assessment_stale_after_correction(client):
    with TestSession() as session:
        land, doc, _ = _create_sample_land_and_doc(session)
        land_id = str(land.id)
        doc_id = str(doc.id)

    # 1. Assess the land
    r_assess = client.post(f"/lands/{land_id}/assess")
    assert r_assess.status_code == 201

    # 2. Case view is not stale
    r_cv1 = client.get(f"/lands/{land_id}/case-view")
    assert r_cv1.status_code == 200
    cv1 = r_cv1.json()
    assert cv1["assessment_stale"] is False
    assert len(cv1["documents"]) == 1
    assert cv1["documents"][0]["file_url_endpoint"] == f"/documents/{doc_id}/file"

    # 3. Apply human correction
    r_patch = client.patch(
        f"/documents/{doc_id}/extraction",
        json={"edits": [{"field_path": "khatian_no", "value": "999"}]},
    )
    assert r_patch.status_code == 200

    # 4. Case view reports assessment_stale == True
    r_cv2 = client.get(f"/lands/{land_id}/case-view")
    assert r_cv2.status_code == 200
    cv2 = r_cv2.json()
    assert cv2["assessment_stale"] is True


def test_get_document_file_url(client):
    with TestSession() as session:
        land, doc, _ = _create_sample_land_and_doc(session)
        doc_id = str(doc.id)

    r = client.get(f"/documents/{doc_id}/file")
    assert r.status_code == 200
    assert "url" in r.json()
    assert "khatian.jpg" in r.json()["url"]
