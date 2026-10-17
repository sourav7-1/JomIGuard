"""Next actions for the buyer, from a rule run and its assessment (spec: docs/specs/actions.md).

Every finding code maps to one clear action filled with its values; coverage gaps and
review_needed add their own; two field checks are always added. At most MAX_ACTIONS, sorted by
priority then severity, always-actions included. Texts never call land safe.
"""

from app.schemas.assessment import Action, Assessment
from app.schemas.land_case import LandCase
from app.services.rules import RuleResult, RuleRun, Status
from app.services.rules.messages import render

MAX_ACTIONS = 6

# code -> (action id, priority, who, template); values come from the finding
FINDING_ACTIONS: dict[str, tuple[str, int, str, str]] = {
    "area_exceeds_share": ("ask_seller_shortfall", 1, "buyer",
        "{seller_names}-কে জিজ্ঞেস করুন বাকি {excess} শতাংশ জমি কোথা থেকে আসছে।"),
    "heir_consent_missing": ("get_co_owner_consent", 1, "seller",
        "{co_owners}-এর লিখিত সম্মতি বা আমমোক্তারনামা নিন।"),
    "seller_not_owner": ("ask_seller_title", 1, "seller",
        "{seller} কীভাবে জমির মালিক হলেন, সেই কাগজ (দলিল, নামজারি বা ওয়ারিশ সনদ) চেয়ে নিন।"),
    "dag_mismatch": ("check_dag_with_amin", 1, "amin",
        "দলিলের দাগ {deed_dag} আর খতিয়ানের দাগ {khatian_dags} একই জমি কিনা, একজন আমিন দিয়ে "
        "নকশা মিলিয়ে দেখুন।"),
    "khatian_mismatch": ("get_certified_khatian", 1, "land_office",
        "দলিলে লেখা {survey} খতিয়ান {deed_khatian_no}-এর সার্টিফায়েড কপি ভূমি অফিস থেকে তুলে "
        "মিলিয়ে নিন।"),
    "mouza_mismatch": ("check_mouza_at_land_office", 1, "land_office",
        "জমিটি কোন মৌজার ({deed_mouza} না {khatian_mouza}), ভূমি অফিসে যাচাই করুন।"),
    "chain_break": ("trace_chain_with_lawyer", 1, "lawyer",
        "{to_document}-এর আগের হস্তান্তরের কাগজ চেয়ে নিন এবং মালিকানার ধারা একজন আইনজীবীকে "
        "দেখান।"),
    "seller_father_mismatch": ("confirm_seller_identity", 2, "seller",
        "{seller}-এর পরিচয় (পিতা/স্বামীর নাম) কাগজ দিয়ে নিশ্চিত হোন।"),
    "heir_missing_from_mutation": ("ask_land_office_heir", 2, "land_office",
        "{heir}-এর নাম নামজারিতে কেন নেই, ভূমি অফিসে জেনে নিন।"),
    "document_missing": ("get_missing_document", 2, "seller",
        "বিক্রেতার কাছ থেকে {missing_document}-এর কপি চেয়ে নিন।"),
    "area_sum_mismatch": ("ask_land_office_shares", 2, "land_office",
        "{document}-এ মালিকদের অংশের যোগফল কেন মেলে না, ভূমি অফিসে জেনে নিন।"),
    "unsupported_unit": ("ask_area_in_shatangsho", 2, "seller",
        "\"{printed}\"-এর পরিমাণ শতাংশে কত, তা বিক্রেতার কাছ থেকে লিখিতভাবে জেনে নিন।"),
    "missing_unit": ("upload_clear_copy", 2, "buyer",
        "{document}-এর পরিষ্কার কপি upload করুন, যাতে জমির একক পড়া যায়।"),
}  # fmt: skip
UPLOAD_ACTION = ("upload_documents", 2, "buyer", "এই কাগজটি upload করুন: {documents}।")
REVIEW_ACTION = ("review_fields", 2, "buyer", "এই তথ্যগুলো নিজে মিলিয়ে নিন: {fields}।")
ALWAYS_ACTIONS = (
    ("amin_field_survey", 3, "amin", "একজন আমিন দিয়ে মাঠে জমি মাপান ও দখল দেখুন।"),
    ("check_mortgage_and_cases", 3, "lawyer",
     "সাব-রেজিস্ট্রি অফিস ও আদালতে বন্ধক বা মামলা আছে কিনা খোঁজ নিন।"),
)  # fmt: skip
SEVERITY = {Status.bad: 0, Status.warn: 1}


def _from_finding(f: RuleResult) -> tuple[int, Action]:
    action_id, priority, who, template = FINDING_ACTIONS[f.code]
    action = Action(
        id=action_id,
        text_bn=render(template, f.values),
        priority=priority,
        who=who,
        from_codes=[f.code],
        sources=f.sources,
    )
    return SEVERITY.get(f.status, 2), action


def _plain(spec, values: dict | None = None) -> Action:
    action_id, priority, who, template = spec
    return Action(id=action_id, text_bn=render(template, values or {}), priority=priority, who=who)


def next_actions(case: LandCase, run: RuleRun, assessment: Assessment) -> list[Action]:
    ranked: list[tuple[int, int, int, Action]] = []  # (priority, severity, order, action)

    def add(severity: int, action: Action) -> None:
        ranked.append((action.priority, severity, len(ranked), action))

    for f in assessment.findings:
        if f.code in FINDING_ACTIONS:
            add(*_from_finding(f))
    if assessment.coverage.documents_missing_bn:
        add(
            2,
            _plain(
                UPLOAD_ACTION, {"documents": " ও ".join(assessment.coverage.documents_missing_bn)}
            ),
        )
    if assessment.review_needed:
        fields = [f"{r.document_label_bn}: {r.label_bn}" for r in assessment.review_needed]
        add(2, _plain(REVIEW_ACTION, {"fields": "; ".join(fields)}))

    seen, actions = set(), []
    for *_, action in sorted(ranked, key=lambda t: t[:3]):
        if action.text_bn not in seen:
            seen.add(action.text_bn)
            actions.append(action)
    always = [_plain(spec) for spec in ALWAYS_ACTIONS]
    return actions[: MAX_ACTIONS - len(always)] + always
