from pathlib import Path

from scenario_loader import load_scenario

from app.services.risk import assess
from app.services.rules import run_rules
from app.services.timeline import build_timeline

SCENARIOS = Path(__file__).parents[1] / "scenarios"


def timeline(name):
    case, _ = load_scenario(SCENARIOS / name)
    result = run_rules(case)
    return build_timeline(case, assess(case, result))


def test_full_chain_scenario_is_in_survey_order_and_all_ok():
    events = timeline("19_full_chain_cs_sa_bs")["events"]
    records = [event for event in events if event["kind"] == "record"]
    assert [event["title_bn"].split("(")[1][:2] for event in records] == ["CS", "SA", "BS"]
    assert all(event["status"] == "ok" for event in events)


def test_proposed_sale_inherits_bad_finding_status():
    proposed = [
        e for e in timeline("01_demo_area_exceeds")["events"] if e["kind"] == "proposed_sale"
    ]
    assert len(proposed) == 1
    assert proposed[0]["status"] == "bad"


def test_broken_chain_marks_linked_event_bad():
    events = timeline("13_chain_break_sa_owner")["events"]
    assert any(e["status"] == "bad" and "chain" in " ".join(e["finding_codes"]) for e in events)


def test_inheritance_shares_only_use_recorded_mutation_or_khatian_values():
    case, _ = load_scenario(SCENARIOS / "19_full_chain_cs_sa_bs")
    result = build_timeline(case, assess(case, run_rules(case)))
    cert = next(e for e in result["events"] if e["kind"] == "inheritance")
    recorded = {
        owner.name: (owner.share_text, owner.share_fraction)
        for doc in case.mutations + ([case.current_khatian] if case.current_khatian else [])
        for owner in doc.data.owners
    }
    for heir in cert["to_owners"]:
        assert (heir["share_text"], heir["share_fraction"]) == recorded.get(
            heir["name"], (None, None)
        )
