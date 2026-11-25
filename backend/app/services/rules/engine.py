"""Run registered rules over a LandCase.

Deterministic order (group as in findings.md, then rule id). A missing required role gives one
"skipped" result instead of a call; an exception inside a rule gives one "error" result and
never stops the other rules. Only bad and warn results are findings.

OCR guard: a document read by the Tesseract fallback (CaseDocument.ocr_read) has untrusted
numbers. A bad/warn result of a numeric group (area: share sums, area comparisons) that uses
such a document, or a result whose values["number_source_ids"] lists one (co_owner_consent:
the sale vs share numbers), becomes a "skipped" result titled "যাচাই করা যায়নি / মিলিয়ে নিন" (listed in
RuleRun.to_verify; it never raises the risk level). Other findings (identifiers, names) stay,
with an OCR note added to the message.
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
    to_verify: list[RuleResult] = Field(default_factory=list)  # OCR numbers: check by hand
    engine_version: str = ENGINE_VERSION


OCR_NUMERIC_GROUPS = ("area",)


def _ocr_guard(case: LandCase, result: RuleResult) -> RuleResult:
    if result.status not in (Status.bad, Status.warn):
        return result
    ocr_labels = {d.source_id: d.label_bn for d in case.documents if d.ocr_read}
    used = [ocr_labels[s.source_id] for s in result.sources if s.source_id in ocr_labels]
    # documents whose numbers triggered the result: every source for the area group; for other
    # rules only what they list in values["number_source_ids"] (co_owner_consent: the sale
    # vs share computation of sold_within_share)
    if result.group in OCR_NUMERIC_GROUPS:
        numbers = used
    else:
        ids = result.values.get("number_source_ids") or []
        numbers = [ocr_labels[i] for i in ids if i in ocr_labels]
    if not used and not numbers:
        return result
    values = {**result.values, "ocr_read": True}
    if numbers:
        docs = ", ".join(dict.fromkeys(numbers))  # unique, in source order
        reason = messages.OCR_NUMBERS_BN.format(docs=docs, message=result.message_bn)
        values["ocr_original_code"] = result.code
        values["ocr_original_title"] = result.title_bn
        return result.model_copy(update={
            "code": None, "status": Status.skipped, "title_bn": messages.OCR_UNVERIFIED_TITLE,
            "message_bn": reason, "skip_reason": reason, "values": values,
        })  # fmt: skip
    note = messages.OCR_NOTE_BN.format(docs=", ".join(dict.fromkeys(used)))
    return result.model_copy(update={"message_bn": result.message_bn + note, "values": values})


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
    results = [
        _ocr_guard(case, r) for rule in sorted(rules, key=_order) for r in _run_one(rule, case)
    ]
    return RuleRun(
        results=results,
        findings=[r for r in results if r.status in (Status.bad, Status.warn)],
        passed=[r for r in results if r.status == Status.passed],
        skipped=[r for r in results if r.status == Status.skipped],
        errors=[r for r in results if r.status == Status.error],
        to_verify=[r for r in results if r.status == Status.skipped and r.values.get("ocr_read")],
    )
