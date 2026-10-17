"""Rule framework: RuleResult, the Rule base class and the registry.

A rule is one file in services/rules/ with a @register-ed Rule subclass; the package imports
every module, so nothing else needs to change. Rules read a LandCase and return results; they
never touch the DB or the network.
"""

import enum
from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import BaseModel, Field

from app.schemas.land_case import CaseRole, LandCase, SourceRef
from app.services.rules import messages
from app.services.rules.codes import CODES


class Status(enum.StrEnum):
    passed = "pass"
    bad = "bad"
    warn = "warn"
    skipped = "skipped"
    error = "error"


class RuleResult(BaseModel):
    rule_id: str
    rule_version: str
    code: str | None = None  # a findings.md code for bad/warn; None otherwise
    group: str
    status: Status
    title_bn: str
    message_bn: str
    values: dict = Field(default_factory=dict)  # machine-readable numbers and names
    sources: list[SourceRef] = Field(default_factory=list)
    skip_reason: str | None = None  # Bangla, for skipped


class Rule(ABC):
    id: ClassVar[str]
    group: ClassVar[str]
    version: ClassVar[str]
    required_roles: ClassVar[tuple[CaseRole, ...]] = ()
    codes: ClassVar[tuple[str, ...]] = ()  # finding codes this rule can produce
    description: ClassVar[str] = ""

    @abstractmethod
    def check(self, case: LandCase) -> list[RuleResult]: ...

    # --- result helpers ---

    def _result(self, **kw) -> RuleResult:
        return RuleResult(rule_id=self.id, rule_version=self.version, group=self.group, **kw)

    def finding(self, code: str, values: dict, sources: list[SourceRef]) -> RuleResult:
        if code not in self.codes:
            raise ValueError(f"rule {self.id} does not declare code {code}")
        title, template = messages.FINDINGS[code]
        return self._result(
            code=code,
            status=Status(CODES[code].severity),
            title_bn=title,
            message_bn=messages.render(template, values),
            values=values,
            sources=sources,
        )

    def passed(self, values: dict, sources: list[SourceRef]) -> RuleResult:
        title, template = messages.PASSES[self.id]
        return self._result(
            status=Status.passed,
            title_bn=title,
            message_bn=messages.render(template, values),
            values=values,
            sources=sources,
        )

    def skipped(self, reason_bn: str) -> RuleResult:
        return self._result(
            status=Status.skipped,
            title_bn=messages.SKIPPED_TITLE,
            message_bn=reason_bn,
            skip_reason=reason_bn,
        )


RULES: dict[str, type[Rule]] = {}


def register(rule: type[Rule]) -> type[Rule]:
    if rule.id in RULES and RULES[rule.id] is not rule:
        raise ValueError(f"duplicate rule id {rule.id}")
    unknown = [c for c in rule.codes if c not in CODES]
    if unknown:
        raise ValueError(f"rule {rule.id}: unknown codes {unknown}")
    RULES[rule.id] = rule
    return rule
