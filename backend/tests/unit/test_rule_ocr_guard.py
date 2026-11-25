"""OCR guard (rules/engine.py): numbers read by the Tesseract fallback never make a mismatch.

Numeric findings (share sums, area comparisons) on an OCR-read document become "যাচাই করা
যায়নি / মিলিয়ে নিন" and do not raise the risk level; the same case read by AI still raises
them. Identifier and name findings stay, with an OCR note.
"""

from pathlib import Path

from scenario_loader import load_scenario

from app.services.risk import HEADLINES_BN, assess
from app.services.rules import RULES, Status, run_rules
from app.services.rules.messages import OCR_UNVERIFIED_TITLE

SCENARIOS = Path(__file__).parents[1] / "scenarios"


def case_of(name: str, ocr: set[str] = frozenset()):
    """Scenario case; documents whose source_id is in `ocr` count as read by Tesseract."""
    case, _ = load_scenario(SCENARIOS / name)
    for doc in case.documents:
        doc.ocr_read = doc.source_id in ocr
    return case


def khatian_id(case) -> str:
    return case.current_khatian.source_id


def risk_without(case, rule_id: str) -> str:
    """The risk level the case would have if this rule did not exist."""
    run = run_rules(case, [r for r in RULES if r != rule_id])
    return assess(case, run).risk_level


# --- share sums ---


def test_ai_read_khatian_still_raises_the_share_sum_mismatch():
    run = run_rules(case_of("11_owner_shares_sum_900"))
    [finding] = [f for f in run.findings if f.code == "area_sum_mismatch"]
    assert finding.status == Status.warn and "OCR" not in finding.message_bn
    assert run.to_verify == []


def test_ocr_read_khatian_gives_no_share_sum_mismatch():
    plain = case_of("11_owner_shares_sum_900")
    case = case_of("11_owner_shares_sum_900", ocr={khatian_id(plain)})
    run = run_rules(case)
    assert "area_sum_mismatch" not in [f.code for f in run.findings]
    [item] = [r for r in run.to_verify if r.rule_id == "shares_add_up"]
    assert item.status == Status.skipped and item.title_bn == OCR_UNVERIFIED_TITLE
    assert "OCR" in item.message_bn and "আসল কাগজের সঙ্গে" in item.message_bn
    assert item.values["ocr_original_code"] == "area_sum_mismatch" and item.sources  # still linked
    assert item.values["ocr_original_title"] == "মালিকদের অংশের যোগফল মেলেনি"

    assessment = assess(case, run)
    assert assessment.risk_level == risk_without(case, "shares_add_up")  # OCR adds no risk
    assert [r.rule_id for r in assessment.to_verify] == ["shares_add_up"]
    assert any("OCR" in c.reason_bn for c in assessment.coverage.checks_skipped)
    assert assessment.headline_bn != HEADLINES_BN["low"]  # never the clean headline


# --- area comparison: an OCR document on either side is enough ---


def test_ocr_read_deed_turns_area_exceeds_share_into_check_by_hand():
    plain = case_of("01_demo_area_exceeds")
    assert "area_exceeds_share" in [f.code for f in run_rules(plain).findings]

    case = case_of("01_demo_area_exceeds", ocr={plain.proposed_deed.source_id})
    run = run_rules(case)
    assert "area_exceeds_share" not in [f.code for f in run.findings]
    moved = {r.values["ocr_original_code"] for r in run.to_verify}
    assert moved == {"area_exceeds_share", "heir_consent_missing"}  # both rest on the sale numbers
    assert assess(case, run).risk_level == risk_without(case, "sold_within_share")


# --- identifiers and names keep the mismatch, with the OCR note ---


def test_identifier_mismatch_on_ocr_document_stays_with_a_note():
    plain = case_of("08_dag_mismatch")
    [before] = [f for f in run_rules(plain).findings if f.code == "dag_mismatch"]
    assert "OCR" not in before.message_bn

    case = case_of("08_dag_mismatch", ocr={khatian_id(plain)})
    [after] = [f for f in run_rules(case).findings if f.code == "dag_mismatch"]
    assert after.status == Status.bad and after.values["ocr_read"] is True
    assert after.message_bn.startswith(before.message_bn) and "OCR দিয়ে পড়া" in after.message_bn
    assert assess(case, run_rules(case)).risk_level == "high"


# --- heir_consent_missing: follows the numbers of the sale vs share check ---


def consent(run):
    found = [f for f in run.findings if f.code == "heir_consent_missing"]
    moved = [
        r for r in run.to_verify if r.values.get("ocr_original_code") == "heir_consent_missing"
    ]
    return found, moved


def test_heir_consent_stays_a_mismatch_when_the_numbers_were_ai_read():
    plain = case_of("01_demo_area_exceeds")
    found, moved = consent(run_rules(plain))
    assert len(found) == 1 and moved == [] and "OCR" not in found[0].message_bn
    assert found[0].values["number_source_ids"]  # the sale check's documents are recorded


def test_heir_consent_moves_to_verify_when_the_sale_numbers_were_ocr_read():
    plain = case_of("01_demo_area_exceeds")
    case = case_of("01_demo_area_exceeds", ocr={khatian_id(plain)})  # shares and plot area
    found, [item] = consent(run_rules(case))
    assert found == [] and item.status == Status.skipped
    assert item.title_bn == OCR_UNVERIFIED_TITLE and "OCR" in item.message_bn


def test_heir_consent_with_only_an_ocr_read_name_document_keeps_the_mismatch_with_a_note():
    plain = case_of("01_demo_area_exceeds")
    [before] = consent(run_rules(plain))[0]
    assert "heir_cert.json" not in before.values["number_source_ids"]  # names, not numbers
    case = case_of("01_demo_area_exceeds", ocr={"heir_cert.json"})
    found, moved = consent(run_rules(case))
    assert moved == [] and len(found) == 1 and found[0].status == before.status
    assert (
        found[0].message_bn.startswith(before.message_bn) and "OCR দিয়ে পড়া" in found[0].message_bn
    )
