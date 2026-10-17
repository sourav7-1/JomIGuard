from pathlib import Path

import pytest
from scenario_loader import load_scenario

from app.services.risk import DISCLAIMER_BN, HEADLINES_BN, assess, forbidden_words_in
from app.services.rules import run_rules

SCENARIOS = Path(__file__).parents[1] / "scenarios"


def assessed(name: str, flags: dict | None = None):
    case, _ = load_scenario(SCENARIOS / name)
    for source_id, field_flags in (flags or {}).items():
        next(d for d in case.documents if d.source_id == source_id).field_flags = field_flags
    return assess(case, run_rules(case))


@pytest.mark.parametrize(
    ("scenario", "level"),
    [
        ("02_sells_within_share", "low"),  # no findings
        ("20_seller_father_mismatch", "medium"),  # warn only
        ("08_dag_mismatch", "high"),  # bad
        ("01_demo_area_exceeds", "high"),  # bad + warn
    ],
)
def test_risk_level_per_finding_mix(scenario, level):
    a = assessed(scenario)
    assert a.risk_level == level and a.headline_bn == HEADLINES_BN[level]


def test_coverage_incomplete_does_not_change_risk():
    a = assessed("02_sells_within_share")  # no older khatian: the chain rule is skipped
    assert a.risk_level == "low"
    assert a.coverage.complete is False
    assert [s.rule_id for s in a.coverage.checks_skipped] == ["ownership_chain"]
    assert a.coverage.documents_missing == ["older_khatian"]
    assert a.coverage.documents_missing_bn == ["পুরোনো খতিয়ান"]
    assert all(s.reason_bn for s in a.coverage.checks_skipped)


def test_summary_counts_in_bangla_digits():
    a = assessed("01_demo_area_exceeds")
    assert a.summary_bn.startswith("১১টা পরীক্ষার মধ্যে ১টায় বড় অমিল আর ১টায় তথ্য অসম্পূর্ণ")
    assert "১টা পরীক্ষা চালানো যায়নি" in a.summary_bn
    low = assessed("19_full_chain_cs_sa_bs")  # everything could run
    assert low.coverage.complete and "সবগুলোতে কাগজ মিলেছে" in low.summary_bn


def test_passed_and_findings_lists():
    a = assessed("01_demo_area_exceeds")
    assert {f.code for f in a.findings} == {"area_exceeds_share", "heir_consent_missing"}
    assert a.passed and all(p.code is None for p in a.passed)
    assert a.disclaimer_bn == DISCLAIMER_BN


def test_headlines_and_disclaimer_have_no_forbidden_words():
    for text in [*HEADLINES_BN.values(), DISCLAIMER_BN]:
        assert forbidden_words_in(text) == [], text
    # the check itself still catches a forbidden word outside the disclaimer's negation
    assert forbidden_words_in("এই জমি নিরাপদ") == ["নিরাপদ"]
    assert forbidden_words_in("100% safe") == ["safe"]


def test_review_needed_lists_low_confidence_fields_used_by_rules():
    flags = {
        "khatian_bs.json": {
            "owners[0].share_text": ["low"],  # used by sold_within_share
            "annual_revenue_text": ["low"],  # not used by any rule
            "plots[0].dag_no": ["high"],  # high confidence: no review
        }
    }
    a = assessed("01_demo_area_exceeds", flags)
    [item] = a.review_needed
    assert (item.source_id, item.field_path) == ("khatian_bs.json", "owners[0].share_text")
    assert item.label_bn == "অংশ" and item.printed_text == ".৪০০"
    assert item.document_label_bn == "বর্তমান খতিয়ান (BS ৮৮২)" and item.flags == ["low"]


def test_normalize_warning_flags_alone_are_not_review_items():
    a = assessed("15_unsupported_unit_katha")  # deed flags: unsupported_unit (a finding)
    assert a.review_needed == []
