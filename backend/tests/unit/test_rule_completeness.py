from pathlib import Path

from scenario_loader import load_scenario

from app.schemas.land_case import CaseRole
from app.services.rules import Status, run_rules

SCENARIOS = Path(__file__).parents[1] / "scenarios"


def title_result(case):
    [result] = run_rules(case, ["title_documents"]).results
    return result


def without_role(case, role):
    return case.model_copy(update={"documents": [d for d in case.documents if d.role != role]})


def with_title(case, title):
    deed = case.proposed_deed
    deed.data = deed.data.model_copy(update={"title_source_text": title})
    return case


def test_inheritance_without_heir_cert_is_document_missing():
    case, _ = load_scenario(SCENARIOS / "14_heir_cert_missing")
    r = title_result(case)
    assert (r.code, r.status) == ("document_missing", Status.warn)
    assert "ওয়ারিশ সনদ" in r.message_bn and "ওয়ারিশ সূত্রে প্রাপ্ত" in r.message_bn
    [src] = r.sources
    assert (src.source_id, src.field_path) == ("deed.json", "title_source_text")
    assert src.printed_text == "পিতা রহমানের মৃত্যুতে ওয়ারিশ সূত্রে প্রাপ্ত"
    assert r.values["missing_role"] == "heir_cert"


def test_inheritance_with_heir_cert_passes():
    case, _ = load_scenario(SCENARIOS / "01_demo_area_exceeds")
    r = title_result(case)
    assert r.status == Status.passed and r.code is None and r.sources


def test_purchase_passes_without_heir_cert():
    case, _ = load_scenario(SCENARIOS / "01_demo_area_exceeds")
    case = with_title(without_role(case, CaseRole.heir_cert), "ক্রয় সূত্রে প্রাপ্ত")
    assert title_result(case).status == Status.passed


def test_no_proposed_deed_is_skipped():
    case, _ = load_scenario(SCENARIOS / "01_demo_area_exceeds")
    r = title_result(without_role(case, CaseRole.proposed_deed))
    assert r.status == Status.skipped and "বিক্রয় দলিল" in r.skip_reason


def test_unreadable_title_is_skipped():
    case, _ = load_scenario(SCENARIOS / "14_heir_cert_missing")
    assert title_result(with_title(case, None)).status == Status.skipped
