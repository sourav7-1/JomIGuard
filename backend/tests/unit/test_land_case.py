import json
import uuid
from pathlib import Path

import pytest
from conftest import TestSession
from scenario_loader import load_scenario

from app.models import DocStatus, DocType, Document, Extraction, ExtractionStatus
from app.schemas.extracted import DeedData, KhatianData
from app.schemas.land_case import CaseDocumentInput, CaseRole, ref
from app.services.land_case import build_land_case, load_land_case

TESTS = Path(__file__).parents[1]
SCENARIOS = sorted(p for p in (TESTS / "scenarios").iterdir() if p.is_dir())
SAMPLES = TESTS / "fixtures/samples"


def sample(name: str) -> dict:
    return json.loads((SAMPLES / f"{name}.json").read_text(encoding="utf-8"))


def khatian(source_id: str, survey: str = "BS", no: str = "882") -> CaseDocumentInput:
    data = KhatianData.model_validate(
        {**sample("khatian"), "survey_type": survey, "khatian_no": no}
    )
    return CaseDocumentInput(source_id=source_id, data=data)


def deed(source_id: str, **changes) -> CaseDocumentInput:
    return CaseDocumentInput(
        source_id=source_id, data=DeedData.model_validate({**sample("deed"), **changes})
    )


@pytest.mark.parametrize("folder", SCENARIOS, ids=lambda p: p.name)
def test_every_scenario_builds_without_warnings(folder):
    case, expected = load_scenario(folder)
    assert case.builder_warnings == []
    assert case.current_khatian is not None and case.proposed_deed is not None
    assert all(d.role != CaseRole.unknown and d.label_bn for d in case.documents)
    assert len(case.documents) == len([p for p in folder.glob("*.json")]) - 1
    assert expected["expected_findings"] is not None


def test_scenario_19_full_chain_roles():
    case, _ = load_scenario(TESTS / "scenarios/19_full_chain_cs_sa_bs")
    assert case.current_khatian.source_id == "khatian_bs.json"
    assert [d.data.survey_type for d in case.older_khatians] == ["SA", "CS"]
    assert [d.source_id for d in case.prior_deeds] == ["deed_prior_1985.json"]
    assert case.proposed_deed.source_id == "deed.json"
    assert [d.source_id for d in case.mutations] == ["mutation.json"]
    assert [d.source_id for d in case.heir_certs] == ["heir_cert.json"]
    assert {t: len(ds) for t, ds in case.documents_by_type.items()} == {
        "deed": 2, "heir_cert": 1, "khatian": 3, "dcr": 1}  # fmt: skip


def test_scenario_01_labels():
    case, _ = load_scenario(TESTS / "scenarios/01_demo_area_exceeds")
    labels = {d.source_id: d.label_bn for d in case.documents}
    assert case.proposed_deed.source_id == "deed.json" and case.proposed_deed.data.is_draft
    assert labels == {
        "deed.json": "বিক্রয় দলিলের খসড়া",
        "deed_prior_1985.json": "বায়া দলিল (১৯৮৫)",
        "heir_cert.json": "ওয়ারিশ সনদ",
        "khatian_bs.json": "বর্তমান খতিয়ান (BS ৮৮২)",
        "mutation.json": "নামজারি (কেস ৫১২/১৮)",
    }


def test_scenario_with_unit_warning_is_needs_review():
    case, _ = load_scenario(TESTS / "scenarios/15_unsupported_unit_katha")
    assert case.proposed_deed.extraction_status == "needs_review"
    assert case.proposed_deed.field_flags["transferred_area_text"] == ["unsupported_unit"]
    assert case.current_khatian.extraction_status == "ok"


def test_two_newest_khatians_warn():
    case = build_land_case([khatian("a", "BS"), khatian("b", "CITY", "17"), khatian("c", "SA")])
    [w] = case.builder_warnings
    assert w.code == "multiple_current_khatians" and w.source_ids == ["a", "b"] and w.message_bn
    assert case.current_khatian.source_id == "a"
    assert [d.source_id for d in case.older_khatians] == ["b", "c"]


def test_two_drafts_warn():
    case = build_land_case([deed("d1"), deed("d2")])
    [w] = case.builder_warnings
    assert w.code == "multiple_proposed_deeds" and w.source_ids == ["d1", "d2"]
    assert case.proposed_deed.source_id == "d1"


def test_without_a_draft_the_latest_registered_deed_is_proposed():
    old = deed("old", is_draft=False, deed_no="3310", deed_year="1985",
               registration_date="1985-06-12")  # fmt: skip
    new = deed("new", is_draft=False, deed_no="4521", deed_year="2019",
               registration_date="2019-02-01")  # fmt: skip
    case = build_land_case([old, new])
    assert case.proposed_deed.source_id == "new" and case.builder_warnings == []
    assert case.proposed_deed.label_bn == "বিক্রয় দলিল (নং ৪৫২১)"
    assert [d.label_bn for d in case.prior_deeds] == ["বায়া দলিল (১৯৮৫)"]


def test_ref_gives_the_printed_text():
    case, _ = load_scenario(TESTS / "scenarios/01_demo_area_exceeds")
    k = case.current_khatian
    share = ref(k, "owners[0].share_fraction")
    assert share.printed_text == ".৪০০" and share.source_id == "khatian_bs.json"
    assert share.label_bn == "বর্তমান খতিয়ান (BS ৮৮২)"
    assert ref(k, "owners[0].share_shatangsho").printed_text == ".৪০০"
    assert ref(k, "plots[0].dag_no").printed_text == "305"
    assert ref(k, "plots[0].area_shatangsho").printed_text == ".১৫০০"
    assert ref(case.proposed_deed, "transferred_area_shatangsho").printed_text == "১০ শতাংশ"
    assert ref(case.proposed_deed, "sellers[0].name_normalized").printed_text == "রহিম উদ্দিন"


# --- database ---


def add_document(db, land_id, status, extraction=None, doc_type=DocType.khatian) -> Document:
    doc_id = uuid.uuid4()
    doc = Document(id=doc_id, land_id=land_id, doc_type=doc_type, status=status,
                   file_key=f"{doc_id}/x.png", original_filename="x.png")  # fmt: skip
    db.add(doc)
    db.flush()
    if extraction is not None:
        db.add(Extraction(document_id=doc_id, extractor="fake", status=ExtractionStatus.ok,
                          data=extraction, warnings=[], field_flags={}))  # fmt: skip
    db.commit()
    return doc


def make_land(client) -> str:
    r = client.post("/lands", json={"mouza": "চাঁদশী", "dag_no": "305"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_load_land_case_skips_failed_and_unread_documents(client):
    land_id = uuid.UUID(make_land(client))
    with TestSession() as db:
        good = add_document(db, land_id, DocStatus.done, sample("khatian"))
        failed = add_document(db, land_id, DocStatus.failed)
        waiting = add_document(db, land_id, DocStatus.processing)
        add_document(db, None, DocStatus.done, sample("deed"), DocType.deed)  # other land
        case = load_land_case(db, land_id)
    assert [d.source_id for d in case.documents] == [str(good.id)]
    assert case.current_khatian.label_bn == "বর্তমান খতিয়ান (BS ৮৮২)"
    [w] = case.builder_warnings
    assert w.code == "document_not_read"
    assert set(w.source_ids) == {str(failed.id), str(waiting.id)}


def test_land_case_api(client):
    land_id = make_land(client)
    with TestSession() as db:
        doc = add_document(db, None, DocStatus.done, sample("khatian"))
    r = client.patch(f"/documents/{doc.id}", json={"land_id": land_id})
    assert r.status_code == 200 and r.json()["land_id"] == land_id
    body = client.get(f"/lands/{land_id}/case").json()
    assert body["land_id"] == land_id and body["builder_warnings"] == []
    [d] = body["documents"]
    assert d["role"] == "current_khatian" and d["source_id"] == str(doc.id)
    assert d["data"]["owners"][0]["share_text"] == ".৪০০"
    assert client.get(f"/lands/{uuid.uuid4()}/case").status_code == 404


def test_land_and_attach_validation(client):
    r = client.post("/lands", json={"dag_no": "305"})
    assert r.status_code == 422  # mouza is required
    land = client.post("/lands", json={"mouza": "চাঁদশী", "dag_no": "305/1", "khatian_no": "882"})
    assert land.json()["district"] == "" and land.json()["khatian_no"] == "882"
    assert client.patch(f"/documents/{uuid.uuid4()}", json={"land_id": None}).status_code == 404
