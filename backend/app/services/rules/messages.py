"""Bangla texts for rule results. Values are filled in with Bangla digits; areas in শতাংশ.

Never call land safe (CLAUDE.md): say what matched, what did not, and what to do next.
A test renders every template and checks FORBIDDEN_WORDS.
"""

from decimal import Decimal

from app.schemas.land_case import CaseRole
from app.services.normalize import to_bangla_digits

FORBIDDEN_WORDS = ("নিরাপদ", "ঝুঁকিমুক্ত", "ঝুঁকি নেই", "সম্পূর্ণ সঠিক", "safe", "guaranteed")

# code -> (title_bn, message_bn)
FINDINGS: dict[str, tuple[str, str]] = {
    "dag_mismatch": (
        "দাগ নম্বর মেলেনি",
        "দলিলে দাগ {deed_dag}, কিন্তু {khatian}-এ দাগ {khatian_dags}। দলিলের তফসিল ও "
        "খতিয়ান মিলিয়ে দেখুন; জরিপ বদলালে দাগ নম্বর বদলাতে পারে।",
    ),
    "khatian_mismatch": (
        "খতিয়ান নম্বর মেলেনি",
        "দলিলে {survey} খতিয়ান নম্বর {deed_khatian_no}, কিন্তু {khatian}-এ খতিয়ান নম্বর "
        "{khatian_no}। দলিলে উল্লেখ করা খতিয়ানের কপি দিয়ে মিলিয়ে দেখুন।",
    ),
    "mouza_mismatch": (
        "মৌজা মেলেনি",
        "দলিলে মৌজা {deed_mouza} (জে.এল. নং {deed_jl}), কিন্তু {khatian}-এ মৌজা "
        "{khatian_mouza} (জে.এল. নং {khatian_jl})। জমিটি একই মৌজার কিনা যাচাই করুন।",
    ),
    "seller_not_owner": (
        "বিক্রেতা মালিক হিসাবে নেই",
        "দলিলে বিক্রেতা {seller}, কিন্তু {khatian}-এ এই নামে কোনো মালিক নেই "
        "(মালিক: {owners})। বিক্রেতা কীভাবে মালিক হলেন তার কাগজ চেয়ে নিন।",
    ),
    "seller_father_mismatch": (
        "বিক্রেতার পিতা/স্বামীর নাম মেলেনি",
        "বিক্রেতা {seller}-এর পিতা/স্বামীর নাম দলিলে {deed_father}, কিন্তু {khatian}-এ "
        "{khatian_father}। {note}একই ব্যক্তি কিনা যাচাই করুন।",
    ),
    "area_exceeds_share": (
        "অংশের চেয়ে বেশি জমি হস্তান্তর",
        "খতিয়ানে{scope} {seller_names}-এর {share_label} {share} শতাংশ, কিন্তু দলিলে "
        "{transferred} শতাংশ হস্তান্তর করা হচ্ছে। অতিরিক্ত {excess} শতাংশের মালিকানা যাচাই করুন।",
    ),
    "area_sum_mismatch": (
        "মালিকদের অংশের যোগফল মেলেনি",
        "{document}-এ মালিকদের অংশের যোগফল {total_shares}{unit}, কিন্তু পুরো জমি "
        "{expected}{unit}। রেকর্ড সংশোধন হয়েছে কিনা ভূমি অফিসে জেনে নিন।",
    ),
    "unsupported_unit": (
        "জমির একক রূপান্তর করা হয়নি",
        '{document}-এ জমির পরিমাণ "{printed}" এমন এককে লেখা যা app শতাংশে রূপান্তর করে না, '
        "তাই এই পরিমাণ মেলানো যায়নি। শতাংশে পরিমাণ জেনে নিন।",
    ),
    "missing_unit": (
        "জমির একক পড়া যায়নি",
        '{document}-এ জমির পরিমাণ "{printed}"-এর কোনো একক ঘরে বা কলামের শিরোনামে পড়া যায়নি। '
        "পরিষ্কার কপি দিন অথবা একক জেনে নিন।",
    ),
    "heir_consent_missing": (
        "অন্য অংশীদারদের সম্মতি দেখা যাচ্ছে না",
        "বাকি {shortfall} শতাংশ {co_owner_names}-এর অংশ থেকে আসতে হবে। তাঁদের সম্মতি বা সই "
        "কোনো কাগজে নেই। তাঁরা বিক্রিতে রাজি কিনা যাচাই করুন।",
    ),
    "heir_missing_from_mutation": (
        "ওয়ারিশ নামজারিতে নেই",
        "ওয়ারিশ সনদে {heir} ওয়ারিশ হিসাবে আছেন, কিন্তু {record}-এ মালিক হিসাবে নেই"
        "{deceased_note}। নামজারি হালনাগাদ কিনা জেনে নিন।",
    ),
    "chain_break": (
        "মালিকানার ধারা মেলেনি",
        "{from_document}-এর মালিক ({owners}) থেকে {to_document}-এ {person} পর্যন্ত মালিকানার "
        "ধারা মেলে না। মাঝের হস্তান্তরের কাগজ চেয়ে নিন।",
    ),
    "document_missing": (
        "দরকারি কাগজ নেই",
        'দলিলে মালিকানার সূত্র "{title_source_text}" লেখা, কিন্তু কেসে {missing_document} নেই। '
        "{missing_document}-এর কপি যোগ করুন।",
    ),
}

# rule_id -> (title_bn, message_bn) for a passing check
PASSES: dict[str, tuple[str, str]] = {
    "title_documents": (
        "মালিকানার সূত্রের কাগজ",
        "দলিলের মালিকানার সূত্রের জন্য দরকারি কাগজ কেসে আছে।",
    ),
    "plots_on_khatian": ("দাগ নম্বর মিলেছে", "দলিলের দাগ {deed_dag} {khatian}-এ আছে।"),
    "khatian_refs": ("খতিয়ান নম্বর মিলেছে", "দলিলের খতিয়ান নম্বর {ref} মিলেছে।"),
    "mouza_match": ("মৌজা মিলেছে", "মৌজা {deed_mouza} দলিল ও খতিয়ানে একই।"),
    "seller_is_owner": ("বিক্রেতা খতিয়ানের মালিক", "বিক্রেতা {seller} খতিয়ানের মালিক।"),
    "seller_father": (
        "বিক্রেতার পিতা/স্বামীর নাম মিলেছে",
        "বিক্রেতা {seller}-এর পিতা/স্বামীর নাম ({deed_father}) দলিল ও খতিয়ানে একই।",
    ),
    "shares_add_up": (
        "মালিকদের অংশের যোগফল মিলেছে",
        "{document}-এ মালিকদের অংশ মিলিয়ে {whole_text} — মোট জমির সমান।",
    ),
    "sold_within_share": (
        "বিক্রির পরিমাণ অংশের মধ্যে",
        "দলিলে {transferred} শতাংশ হস্তান্তর, যা{scope} {seller_names}-এর {share_label} "
        "{share} শতাংশের মধ্যে।",
    ),
    "units": ("জমির একক পড়া গেছে", "সব জমির পরিমাণ ও অংশের একক পড়া গেছে।"),
    "co_owner_consent": (
        "অন্য অংশীদারের অংশ থেকে জমি আসছে না",
        "অন্য অংশীদারের অংশ থেকে জমি নেওয়া হচ্ছে না।",
    ),
    "heirs_in_mutation": ("ওয়ারিশ নামজারিতে আছেন", "ওয়ারিশ {heir} {record}-এ আছেন{deceased_note}।"),
    "ownership_chain": (
        "মালিকানার ধারা মিলেছে",
        "মালিকানার ধারা {earliest_year} থেকে বর্তমান পর্যন্ত ভাঙেনি: {links}।",
    ),
}

# rule_id -> message when a rule passed for several items (sellers, heirs, dags, documents):
# one ✓ line per rule; the per-item detail stays in values["items"] (risk.condense_passes)
PASSES_MANY: dict[str, str] = {
    "plots_on_khatian": "দলিলের দাগ {deed_dags} সবই {khatian}-এ আছে।",
    "khatian_refs": "দলিলের খতিয়ান নম্বর {refs} মিলেছে।",
    "seller_is_owner": "বিক্রেতা {sellers} সবাই খতিয়ানের মালিক।",
    "seller_father": "{count} জন বিক্রেতার পিতা/স্বামীর নাম দলিল ও খতিয়ানে একই।",
    "shares_add_up": "{documents}-এ মালিকদের অংশ মিলিয়ে {whole_text} — মোট জমির সমান।",
    "sold_within_share": "সব দাগে হস্তান্তর বিক্রেতার অংশের মধ্যে।",
    "heirs_in_mutation": "{count} জন ওয়ারিশই {record}-এ আছেন{deceased_note}।",
}

SKIPPED_TITLE = "যাচাই করা যায়নি"
SKIP_MISSING_ROLES = "এই যাচাইয়ের জন্য {missing} দরকার, যা কেসে নেই।"
ERROR_TITLE = "যাচাইটি চালানো যায়নি"
ERROR_MESSAGE = "এই যাচাইটি চালাতে সমস্যা হয়েছে; ফলাফল দেখানো হচ্ছে না।"

ROLE_LABELS: dict[CaseRole, str] = {
    CaseRole.current_khatian: "বর্তমান খতিয়ান",
    CaseRole.older_khatian: "পুরোনো খতিয়ান",
    CaseRole.proposed_deed: "বিক্রয় দলিল",
    CaseRole.prior_deed: "বায়া দলিল",
    CaseRole.mutation: "নামজারি",
    CaseRole.heir_cert: "ওয়ারিশ সনদ",
    CaseRole.unknown: "অজানা কাগজ",
}


def show(value) -> str:
    """A value as shown to the user: Bangla digits, decimals without trailing zeros."""
    if value is None:
        return "উল্লেখ নেই"
    if isinstance(value, bool):
        return "হ্যাঁ" if value else "না"
    if isinstance(value, Decimal | int | float):
        d = Decimal(str(value)).normalize()
        return to_bangla_digits(format(d, "f"))
    if isinstance(value, list | tuple | set):
        return ", ".join(show(v) for v in value)
    return to_bangla_digits(str(value))


def render(template: str, values: dict) -> str:
    return template.format(**{k: show(v) for k, v in values.items()})
