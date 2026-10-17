import re
import string
from decimal import Decimal
from pathlib import Path

import pytest
from scenario_loader import load_scenario

from app.schemas.land_case import CaseRole, LandCase
from app.services.rules import RULES, Rule, RuleResult, Status, messages, run_rules
from app.services.rules.codes import CODES

HERE = Path(__file__).parent
# repo: <root>/docs; Docker: /docs (read-only mount in docker-compose.yml)
FINDINGS_MD = (HERE.parents[2] / "docs/specs/findings.md").read_text(encoding="utf-8")
CASE, _ = load_scenario(HERE.parent / "scenarios/01_demo_area_exceeds")


def dummy(rule_id, group="identity", roles=(), check=None, codes=("dag_mismatch",)):
    def default(self, case):
        return [self.passed({}, [])]

    attrs = {"id": rule_id, "group": group, "version": "1", "required_roles": roles,
             "codes": codes, "check": check or default}  # fmt: skip
    return type(rule_id, (Rule,), attrs)


@pytest.fixture
def rules(monkeypatch):
    """Register dummy rules for one test; returns their ids."""

    def add(*rule_classes):
        for cls in rule_classes:
            monkeypatch.setitem(RULES, cls.id, cls)
            monkeypatch.setitem(messages.PASSES, cls.id, ("মিলেছে", "মিলেছে।"))
        return [cls.id for cls in rule_classes]

    return add


def test_order_is_group_then_rule_id(rules):
    ids = rules(
        dummy("z_rule", "completeness"),
        dummy("b_rule", "area"),
        dummy("a_rule", "area"),
        dummy("m_rule", "identity"),
    )
    run = run_rules(CASE, ids)
    assert [r.rule_id for r in run.results] == ["m_rule", "a_rule", "b_rule", "z_rule"]
    assert run.engine_version and len(run.passed) == 4


def test_missing_role_is_skipped_without_calling_check(rules):
    def boom(self, case):
        raise AssertionError("must not be called")

    ids = rules(dummy("needs_sa", roles=(CaseRole.older_khatian,), check=boom))
    [r] = run_rules(CASE, ids).results
    assert r.status == Status.skipped and "পুরোনো খতিয়ান" in r.skip_reason


def test_exception_becomes_one_error_and_other_rules_still_run(rules):
    def boom(self, case):
        raise ZeroDivisionError("bad math")

    ids = rules(dummy("broken", check=boom), dummy("fine"))
    run = run_rules(CASE, ids)
    assert [r.status for r in run.results] == [Status.error, Status.passed]
    [err] = run.errors
    assert err.rule_id == "broken" and "ZeroDivisionError" in err.values["error"]
    assert run.findings == []  # an error is never a finding


def test_findings_are_bad_and_warn_only_and_a_rule_may_return_several(rules):
    def several(self, case):
        dag = {"deed_dag": "306", "khatian": "BS ৮৮২", "khatian_dags": ["305"]}
        father = {"seller": "রহিম", "deed_father": "ক", "khatian_father": "খ",
                  "khatian": "BS ৮৮২", "note": ""}  # fmt: skip
        return [
            self.finding("dag_mismatch", dag, []),
            self.finding("seller_father_mismatch", father, []),
            self.passed({}, []),
        ]

    ids = rules(dummy("multi", check=several, codes=("dag_mismatch", "seller_father_mismatch")))
    run = run_rules(CASE, ids)
    assert [(f.code, f.status) for f in run.findings] == [
        ("dag_mismatch", Status.bad),
        ("seller_father_mismatch", Status.warn),
    ]
    assert "৩০৬" in run.findings[0].message_bn and len(run.passed) == 1


def test_undeclared_code_is_an_error(rules):
    def sneaky(self, case):
        return [self.finding("chain_break", {}, [])]

    ids = rules(dummy("sneaky", check=sneaky))
    assert run_rules(CASE, ids).results[0].status == Status.error


def test_empty_case_skips_rules_needing_roles():
    run = run_rules(LandCase())
    assert run.findings == [] and run.errors == []
    needs_roles = {i for i, rule in RULES.items() if rule.required_roles}
    assert needs_roles and all(
        r.status == Status.skipped for r in run.results if r.rule_id in needs_roles
    )


def test_codes_match_findings_md():
    table = re.findall(r"^\| `(\w+)` \| (\w+) \| (bad|warn) \|", FINDINGS_MD, re.MULTILINE)
    assert len(table) == 13
    assert {code: (group, sev) for code, group, sev in table} == {
        c.code: (c.group, c.severity) for c in CODES.values()
    }
    assert set(messages.FINDINGS) == set(CODES)


def placeholders(template: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


def test_templates_never_contain_forbidden_words():
    texts = [
        messages.SKIPPED_TITLE,
        messages.ERROR_TITLE,
        messages.ERROR_MESSAGE,
        messages.SKIP_MISSING_ROLES.format(missing="বর্তমান খতিয়ান"),
        *messages.ROLE_LABELS.values(),
    ]
    for title, template in [*messages.FINDINGS.values(), *messages.PASSES.values()]:
        sample = {name: Decimal("10.5") for name in placeholders(template)}
        texts += [title, messages.render(template, sample)]
    for text in texts:
        for word in messages.FORBIDDEN_WORDS:
            assert word.lower() not in text.lower(), (word, text)


def test_values_are_shown_in_bangla_digits():
    assert messages.show(Decimal("6.000")) == "৬" and messages.show(Decimal("2.50")) == "২.৫"
    assert messages.show(["305", "306/1"]) == "৩০৫, ৩০৬/১"
    values = {"transferred": Decimal("10.00"), "share": Decimal("6.000"), "excess": Decimal(4),
              "scope": "", "seller_names": "রহিম উদ্দিন", "share_label": "অংশ"}  # fmt: skip
    out = messages.render(messages.FINDINGS["area_exceeds_share"][1], values)
    assert "১০ শতাংশ" in out and "৬ শতাংশ" in out and "৪ শতাংশ" in out


def test_every_registered_rule_has_texts():
    for rule in RULES.values():
        assert rule.id in messages.PASSES
        assert all(code in messages.FINDINGS for code in rule.codes)


def test_result_model_round_trips():
    r = RuleResult(rule_id="x", rule_version="1", group="area", status=Status.warn,
                   title_bn="t", message_bn="m")  # fmt: skip
    assert RuleResult.model_validate_json(r.model_dump_json()) == r
