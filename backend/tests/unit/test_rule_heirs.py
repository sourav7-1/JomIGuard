"""Heirs rules on cases built from the scenario documents."""

from decimal import Decimal
from pathlib import Path

from scenario_loader import load_scenario

from app.schemas.land_case import CaseRole
from app.services.rules import Status, run_rules

SCENARIOS = Path(__file__).parents[1] / "scenarios"


def case_of(name: str):
    case, _ = load_scenario(SCENARIOS / name)
    return case


def edit(doc, **changes):
    doc.data = doc.data.model_copy(update=changes)


def without(case, role):
    case.documents = [d for d in case.documents if d.role != role]
    return case


def results(case, rule_id):
    return run_rules(case, [rule_id]).results


# --- co_owner_consent ---


def test_demo_needs_co_heirs_consent():
    [r] = results(case_of("01_demo_area_exceeds"), "co_owner_consent")
    assert (r.code, r.status) == ("heir_consent_missing", Status.warn)
    assert r.values["shortfall"] == Decimal("4")
    assert r.values["co_owners"] == ["করিম উদ্দিন", "সালমা খাতুন"]
    assert r.values["co_owner_shares"] == {"করিম উদ্দিন": ".৪০০", "সালমা খাতুন": ".২০০"}
    assert "বাকি ৪ শতাংশ করিম উদ্দিন বা সালমা খাতুন-এর অংশ থেকে আসতে হবে" in r.message_bn
    assert "সম্মতি বা সই কোনো কাগজে নেই" in r.message_bn
    assert {s.source_id for s in r.sources} == {"deed.json", "heir_cert.json", "khatian_bs.json"}
    shares = {s.value_bn for s in r.sources if s.source_id == "khatian_bs.json"}
    assert shares == {"করিম উদ্দিনের অংশ .৪০০", "সালমা খাতুনের অংশ .২০০"}


def test_all_heirs_selling_together_needs_no_consent():
    assert [r.status for r in results(case_of("05_all_heirs_sell_all"), "co_owner_consent")] == [
        Status.passed
    ]


def test_sale_within_share_passes():
    assert results(case_of("02_sells_within_share"), "co_owner_consent")[0].status == Status.passed


def test_dag_not_on_khatian_is_skipped():
    [r] = results(case_of("18_dag_and_area_mismatch"), "co_owner_consent")
    assert r.status == Status.skipped and "খতিয়ানে নেই" in r.skip_reason


def test_purchase_title_without_heir_cert_gives_no_finding():
    case = without(case_of("01_demo_area_exceeds"), CaseRole.heir_cert)
    edit(case.proposed_deed, title_source_text="ক্রয় সূত্রে প্রাপ্ত")
    [r] = results(case, "co_owner_consent")
    assert r.status == Status.skipped and r.code is None


def test_inheritance_title_without_heir_cert_still_warns():
    case = without(case_of("01_demo_area_exceeds"), CaseRole.heir_cert)
    [r] = results(case, "co_owner_consent")  # title: "... ওয়ারিশ সূত্রে প্রাপ্ত"
    assert r.code == "heir_consent_missing"
    assert {s.field_path for s in r.sources if s.source_id == "deed.json"} >= {"title_source_text"}


def test_co_owners_not_on_the_heir_certificate_give_no_finding():
    case = case_of("01_demo_area_exceeds")
    heir_cert = case.heir_certs[0]
    edit(heir_cert, heirs=[h for h in heir_cert.data.heirs if h.name == "রহিম উদ্দিন"])
    [r] = results(case, "co_owner_consent")
    assert r.status == Status.skipped


def test_seller_not_owner_skips_consent():
    [r] = results(case_of("07_seller_not_owner"), "co_owner_consent")
    assert r.status == Status.skipped


# --- heirs_in_mutation ---


def test_extra_wife_is_missing_from_mutation():
    rs = results(case_of("12_heir_missing_from_mutation"), "heirs_in_mutation")
    findings = [r for r in rs if r.code]
    assert [r.values["heir"] for r in findings] == ["জমিলা খাতুন"]
    [f] = findings
    assert f.status == Status.warn and "নামজারি (কেস ৫১২/১৮)" in f.message_bn
    assert {s.source_id for s in f.sources} == {"heir_cert.json", "mutation.json"}
    assert sum(r.status == Status.passed for r in rs) == 3


def test_deceased_heir_is_skipped_and_named():
    case = case_of("12_heir_missing_from_mutation")
    heir_cert = case.heir_certs[0]
    heirs = [
        h.model_copy(update={"is_deceased": h.name == "জমিলা খাতুন"}) for h in heir_cert.data.heirs
    ]
    edit(heir_cert, heirs=heirs)
    rs = results(case, "heirs_in_mutation")
    assert all(r.status == Status.passed for r in rs) and len(rs) == 3
    assert rs[0].values["skipped_deceased"] == ["জমিলা খাতুন"]
    assert "মৃত হিসাবে চিহ্নিত, তাই বাদ: জমিলা খাতুন" in rs[0].message_bn


def test_without_mutation_the_current_khatian_is_used():
    rs = results(case_of("11_owner_shares_sum_900"), "heirs_in_mutation")  # no mutation
    assert all(r.status == Status.passed for r in rs)
    assert rs[0].values["record"] == "বর্তমান খতিয়ান (BS ৮৮২)"


def test_no_heir_cert_is_skipped():
    [r] = results(case_of("14_heir_cert_missing"), "heirs_in_mutation")
    assert r.status == Status.skipped
