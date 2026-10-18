"""Turn a rule run into an assessment: risk level, Bangla headline and summary, coverage and the
fields a person should check. Never calls land safe (CLAUDE.md); coverage never changes risk.
"""

from collections import defaultdict

from app.schemas.assessment import Assessment, Coverage, ReviewItem, SkippedCheck
from app.schemas.identity import IdentityVerificationOut
from app.schemas.land_case import CaseRole, LandCase
from app.services.normalize import to_bangla_digits
from app.services.rules import RULES, RuleResult, RuleRun, Status
from app.services.rules.messages import FORBIDDEN_WORDS, PASSES_MANY, ROLE_LABELS, render

HEADLINES_BN = {
    "high": "উচ্চ ঝুঁকি: এখনই বায়না দেবেন না",
    "medium": "মাঝারি ঝুঁকি: আগে নিচের বিষয়গুলো যাচাই করুন",
    "low": "কাগজে বড় কোনো অমিল পাওয়া যায়নি",
}
DISCLAIMER_BN = (
    "এই app কখনো জমি নিরাপদ বলে না। কাগজে সব মিললেও মামলা, দখল বা বন্ধক কাগজে ধরা পড়ে না। "
    "তাই app শুধু বলে কী মিলেছে, কী মেলেনি, আর এরপর কী করতে হবে।"
)
# the only allowed use of a forbidden word: the disclaimer's negation
ALLOWED_PHRASES = ("জমি নিরাপদ বলে না",)


DEED_DISCLAIMER_BN = (
    "এই app দলিল আসল না জাল তা প্রমাণ করে না। fingerprint শুধু দেখায় "
    "আমাদের কাছে রাখা কপি পরে বদলেছে কি না। আসলত্বের জন্য সাব-রেজিস্ট্রি "
    "অফিসের সার্টিফাইড কপি দেখুন।"
)


def forbidden_words_in(text: str) -> list[str]:
    """Forbidden words in user-facing text, ignoring the disclaimer's "… নিরাপদ বলে না"."""
    for phrase in ALLOWED_PHRASES:
        text = text.replace(phrase, "")
    text = text.replace(DEED_DISCLAIMER_BN, "")
    words = (*FORBIDDEN_WORDS, "আসল দলিল", "জাল দলিল", "authentic", "genuine", "fake")
    return [w for w in words if w.lower() in text.lower()]


REVIEW_FLAGS = ("low", "medium")  # extraction confidence levels that need a person's check
FIELD_LABELS_BN = {
    "share_text": "অংশ",
    "area_text": "জমির পরিমাণ",
    "plot_total_area_text": "দাগের মোট জমি",
    "khatian_share_text": "দাগে খতিয়ানের অংশ",
    "total_area_text": "মোট জমি",
    "transferred_area_text": "হস্তান্তরিত জমি",
    "dag_no": "দাগ নং",
    "khatian_no": "খতিয়ান নং",
    "name": "নাম",
    "father_or_husband_name": "পিতা/স্বামীর নাম",
    "mouza": "মৌজা",
    "jl_no": "জে.এল. নং",
    "title_source_text": "মালিকানার সূত্র",
    "deceased_name": "মৃত ব্যক্তির নাম",
}


def _helpful_roles(rule_id: str, case: LandCase) -> list[CaseRole]:
    """Documents that would let a skipped rule run (beyond its required roles)."""
    if rule_id == "ownership_chain":  # needs an older khatian and a predecessor
        roles = [CaseRole.older_khatian]
        if not case.heir_certs:
            roles.append(CaseRole.prior_deed)
        return roles
    if rule_id == "heirs_in_mutation":
        return [CaseRole.mutation]
    return []


def risk_level(run: RuleRun) -> str:
    statuses = {f.status for f in run.findings}
    return "high" if Status.bad in statuses else "medium" if Status.warn in statuses else "low"


def _rule_outcomes(run: RuleRun) -> dict[str, str]:
    """rule_id -> worst outcome: bad > warn > pass > skipped > error."""
    order = [Status.bad, Status.warn, Status.passed, Status.skipped, Status.error]
    by_rule: dict[str, set[Status]] = defaultdict(set)
    for r in run.results:
        by_rule[r.rule_id].add(r.status)
    return {rid: next(s for s in order if s in sts) for rid, sts in by_rule.items()}


def _summary(run: RuleRun) -> str:
    outcomes = _rule_outcomes(run)
    ran = [s for s in outcomes.values() if s in (Status.bad, Status.warn, Status.passed)]
    bad = sum(s == Status.bad for s in outcomes.values())
    warn = sum(s == Status.warn for s in outcomes.values())
    skipped = sum(s in (Status.skipped, Status.error) for s in outcomes.values())
    n = to_bangla_digits
    if bad or warn:
        parts = [f"{n(str(bad))}টায় বড় অমিল"] if bad else []
        parts += [f"{n(str(warn))}টায় তথ্য অসম্পূর্ণ"] if warn else []
        text = f"{n(str(len(ran)))}টা পরীক্ষার মধ্যে " + " আর ".join(parts)
    else:
        text = f"{n(str(len(ran)))}টা পরীক্ষার সবগুলোতে কাগজ মিলেছে"
    if skipped:
        text += f"; {n(str(skipped))}টা পরীক্ষা চালানো যায়নি"
    return text + "।"


def _coverage(case: LandCase, run: RuleRun) -> Coverage:
    outcomes = _rule_outcomes(run)
    skipped = [r for r in run.results if r.status in (Status.skipped, Status.error)]
    missing: list[CaseRole] = []
    for rule_id, outcome in outcomes.items():
        if outcome != Status.skipped or rule_id not in RULES:
            continue
        rule = RULES[rule_id]
        for role in (*rule.required_roles, *_helpful_roles(rule_id, case)):
            if not case.with_role(role) and role not in missing:
                missing.append(role)
    return Coverage(
        complete=not skipped,
        checks_run=sum(s in (Status.bad, Status.warn, Status.passed) for s in outcomes.values()),
        checks_skipped=[
            SkippedCheck(rule_id=r.rule_id, reason_bn=r.skip_reason or r.message_bn)
            for r in skipped
        ],
        documents_missing=[r.value for r in missing],
        documents_missing_bn=[ROLE_LABELS[r] for r in missing],
    )


def _printed_path(path: str) -> str:
    """Source field path -> the printed field it comes from (same as ref())."""
    head, _, field = path.rpartition(".")
    if field == "name_normalized":
        field = "name"
    elif field.endswith(("_shatangsho", "_fraction")):
        field = field.rsplit("_", 1)[0] + "_text"
    return f"{head}.{field}" if head else field


def _review_needed(case: LandCase, run: RuleRun) -> list[ReviewItem]:
    used = {(s.source_id, _printed_path(s.field_path)) for r in run.results for s in r.sources}
    items = []
    for doc in case.documents:
        for path, flags in (doc.field_flags or {}).items():
            flags = flags if isinstance(flags, list) else [flags]
            if not any(f in REVIEW_FLAGS for f in flags):
                continue
            if (doc.source_id, _printed_path(path)) not in used:
                continue
            field = path.rpartition(".")[2]
            printed = next(
                (
                    s.printed_text
                    for r in run.results
                    for s in r.sources
                    if s.source_id == doc.source_id and _printed_path(s.field_path) == path
                ),
                None,
            )
            items.append(
                ReviewItem(
                    source_id=doc.source_id,
                    document_label_bn=doc.label_bn,
                    field_path=path,
                    label_bn=FIELD_LABELS_BN.get(field, field),
                    printed_text=printed,
                    flags=[str(f) for f in flags],
                )
            )
    return items


def _unique(values: list) -> list:
    out = []
    for v in values:
        if v not in out:
            out.append(v)
    return out


def condense_passes(run: RuleRun) -> list[RuleResult]:
    """One ✓ per rule that passed: a rule that passed for several sellers, heirs, dags or
    documents becomes one result with a short message; the per-item values go to
    values["items"]. Rules that also produced a finding get no ✓ line."""
    outcomes = _rule_outcomes(run)
    by_rule: dict[str, list[RuleResult]] = {}
    for r in run.passed:
        if outcomes.get(r.rule_id) == Status.passed:
            by_rule.setdefault(r.rule_id, []).append(r)
    out = []
    for rule_id, results in by_rule.items():
        first = results[0]
        if len(results) == 1:
            out.append(
                first.model_copy(update={"values": {**first.values, "items": [first.values]}})
            )
            continue
        values = {**first.values, "count": len(results), "items": [r.values for r in results]}
        for key in first.values:
            options = _unique([r.values.get(key) for r in results])
            values[f"{key}s"] = options
            if len(options) > 1 and key == "whole_text":
                values[key] = "পুরো জমি"
        sources = _unique([s for r in results for s in r.sources])
        template = PASSES_MANY.get(rule_id)
        message = render(template, values) if template else first.message_bn
        out.append(first.model_copy(update={"message_bn": message, "values": values,
                                             "sources": sources}))  # fmt: skip
    return out


def assess(case: LandCase, run: RuleRun) -> Assessment:
    level = risk_level(run)
    return Assessment(
        engine_version=run.engine_version,
        risk_level=level,
        headline_bn=HEADLINES_BN[level],
        summary_bn=_summary(run),
        coverage=_coverage(case, run),
        review_needed=_review_needed(case, run),
        findings=run.findings,
        identity_verifications=[
            IdentityVerificationOut.model_validate(row)
            for row in getattr(case, "identity_records", [])
        ],
        passed=condense_passes(run),
        disclaimer_bn=DISCLAIMER_BN,
    )
