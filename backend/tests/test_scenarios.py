"""The answer key: every scenario's findings must match its expected.json.

Codes without a rule yet make the scenario xfail ("rule not implemented"); as soon as a rule
declares a code, that code is checked strictly. A scenario that expects nothing fails on any
finding (no false alarms).
"""

from pathlib import Path

import pytest
from scenario_loader import load_scenario

from app.services.risk import assess
from app.services.rules import RULES, run_rules

SCENARIOS = sorted(p for p in (Path(__file__).parent / "scenarios").iterdir() if p.is_dir())


def implemented_codes() -> set[str]:
    return {code for rule in RULES.values() for code in rule.codes}


@pytest.mark.parametrize("folder", SCENARIOS, ids=lambda p: p.name)
def test_scenario(folder: Path):
    case, expected = load_scenario(folder)
    run = run_rules(case)
    assert run.errors == [], [e.values for e in run.errors]

    got: dict[str, tuple[str, set[str]]] = {}
    for f in run.findings:
        _, docs = got.setdefault(f.code, (f.status.value, set()))
        docs.update(s.source_id for s in f.sources)
    implemented = implemented_codes()
    want = {
        f["code"]: (f["severity"], set(f["documents"]))
        for f in expected["expected_findings"]
        if f["code"] in implemented
    }
    # same codes and severities; every expected document is cited (a finding may cite more,
    # e.g. heir_consent_missing also cites the khatian the co-owners' shares come from)
    assert {c: sev for c, (sev, _) in got.items()} == {c: sev for c, (sev, _) in want.items()}, (
        f"findings differ: got {got}, expected {want}"
    )
    for code, (_, docs) in want.items():
        assert docs <= got[code][1], f"{code}: expected documents {docs}, cited {got[code][1]}"
    assert assess(case, run).risk_level == expected["expected_risk"]

    missing = sorted({f["code"] for f in expected["expected_findings"]} - implemented)
    if missing:
        pytest.xfail(f"rule not implemented: {', '.join(missing)}")
