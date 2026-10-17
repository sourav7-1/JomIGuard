"""Run registered rules over a LandCase.

Deterministic order (group as in findings.md, then rule id). A missing required role gives one
"skipped" result instead of a call; an exception inside a rule gives one "error" result and
never stops the other rules. Only bad and warn results are findings.
"""

from pydantic import BaseModel, Field

from app.schemas.land_case import LandCase
from app.services.rules import messages
from app.services.rules.base import RULES, Rule, RuleResult, Status
from app.services.rules.codes import GROUP_ORDER

ENGINE_VERSION = "1"


class RuleRun(BaseModel):
    results: list[RuleResult] = Field(default_factory=list)
    findings: list[RuleResult] = Field(default_factory=list)  # bad + warn only
    passed: list[RuleResult] = Field(default_factory=list)
    skipped: list[RuleResult] = Field(default_factory=list)
    errors: list[RuleResult] = Field(default_factory=list)
    engine_version: str = ENGINE_VERSION


def _order(rule: type[Rule]) -> tuple[int, str]:
    group = GROUP_ORDER.index(rule.group) if rule.group in GROUP_ORDER else len(GROUP_ORDER)
    return group, rule.id


def _run_one(rule_cls: type[Rule], case: LandCase) -> list[RuleResult]:
    rule = rule_cls()
    missing = [r for r in rule.required_roles if not case.with_role(r)]
    if missing:
        names = ", ".join(messages.ROLE_LABELS[r] for r in missing)
        return [rule.skipped(messages.SKIP_MISSING_ROLES.format(missing=names))]
    try:
        results = list(rule.check(case))
        if not all(isinstance(r, RuleResult) for r in results):
            raise TypeError("check() must return RuleResult objects")
        return results
    except Exception as e:  # noqa: BLE001  isolate a broken rule; never a finding
        return [
            RuleResult(
                rule_id=rule.id,
                rule_version=rule.version,
                group=rule.group,
                status=Status.error,
                title_bn=messages.ERROR_TITLE,
                message_bn=messages.ERROR_MESSAGE,
                values={"error": f"{type(e).__name__}: {e}"},
            )
        ]


def run_rules(case: LandCase, rule_ids: list[str] | None = None) -> RuleRun:
    rules = [RULES[i] for i in rule_ids] if rule_ids is not None else list(RULES.values())
    results = [r for rule in sorted(rules, key=_order) for r in _run_one(rule, case)]
    return RuleRun(
        results=results,
        findings=[r for r in results if r.status in (Status.bad, Status.warn)],
        passed=[r for r in results if r.status == Status.passed],
        skipped=[r for r in results if r.status == Status.skipped],
        errors=[r for r in results if r.status == Status.error],
    )
