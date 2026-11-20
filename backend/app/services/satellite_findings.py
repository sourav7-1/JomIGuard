"""Paper vs ground: turn a sentinel analyze-area result and the khatian into findings.

The findings use the RuleResult shape but are a separate group ("স্যাটেলাইট যাচাই"); they never
change the document rules' outcomes or the risk level. Satellite pixels are 10 m, so every
message says it describes the area around the plot, not the plot itself. There is no "pass":
when nothing is seen, there are simply no satellite findings.
"""

import re

from app.schemas.land_case import LandCase
from app.services.normalize import to_bangla_digits
from app.services.rules.base import RuleResult, Status

GROUP = "satellite"
GROUP_TITLE_BN = "স্যাটেলাইট যাচাই"
RULE_VERSION = "1"
MIN_GOOD_YEARS = 4

# Bangla land classes, matched as whole words ("নালা" is a drain, not "নাল" cropland)
AGRI_CLASSES = ("নাল", "ধানী", "ধানি", "কৃষি", "ফসলি", "চাষ", "চাষাবাদ")
ORCHARD_CLASSES = ("বাগান", "বাগিচা")
_WORD_SPLIT = re.compile(r"[\s,;:/()\[\]\-।.'\"]+")


def area_note_bn(buffer_m: float) -> str:
    m = to_bangla_digits(f"{buffer_m:.0f}")
    return f"এটি প্লটের চারপাশের প্রায় {m} মিটার এলাকার স্যাটেলাইট ছবি থেকে, প্লটের সীমানার ভেতরের হিসাব নয়।"


def _years_bn(years) -> str:
    return ", ".join(to_bangla_digits(str(y)) for y in years)


def _num_bn(value: float) -> str:
    return to_bangla_digits(f"{value:.1f}".rstrip("0").rstrip("."))


def _words(text: str | None) -> set[str]:
    return {w for w in _WORD_SPLIT.split(text or "") if w}


def land_classes(case: LandCase) -> list[str]:
    """Printed land classes of the current khatian's plots (any khatian if there is none)."""
    khatians = [case.current_khatian] if case.current_khatian else case.older_khatians
    out = []
    for doc in khatians:
        for plot in getattr(doc.data, "plots", None) or []:
            if plot.land_class and plot.land_class not in out:
                out.append(plot.land_class)
    return out


def is_agricultural(land_class: str) -> bool:
    return bool(_words(land_class) & set(AGRI_CLASSES))


def is_orchard(land_class: str) -> bool:
    words = _words(land_class)
    return any(w in ORCHARD_CLASSES or w.endswith("বাগান") for w in words)


def _finding(
    kind: str, status: Status, title: str, body: str, action: str, buffer_m: float, values: dict
) -> RuleResult:
    message = f"{body} {area_note_bn(buffer_m)}"
    return RuleResult(
        rule_id=f"satellite_{kind}",
        rule_version=RULE_VERSION,
        code=f"satellite_{kind}" if status in (Status.bad, Status.warn) else None,
        group=GROUP,
        status=status,
        title_bn=title,
        message_bn=message,
        values={**values, "next_action_bn": action, "buffer_m": buffer_m, "scope": "surroundings"},
        skip_reason=message if status == Status.skipped else None,
    )


def _good_years(result: dict) -> list[int]:
    signals = result.get("signals") or {}
    bad = set(signals.get("outlier_years") or []) | set(signals.get("low_confidence_years") or [])
    return [
        y["year"]
        for y in result.get("years") or []
        if y.get("status") == "ok" and not y.get("low_confidence") and y["year"] not in bad
    ]


def satellite_findings(result: dict, case: LandCase | None = None) -> list[RuleResult]:
    buffer_m = float(result.get("buffer_m") or 200)
    signals = result.get("signals") or {}
    tree = (result.get("trends") or {}).get("tree_cover_pct") or {}
    heavy = list(signals.get("water_heavy_years") or [])
    spikes = list(signals.get("water_spike_years") or [])
    good = _good_years(result)
    enough = len(good) >= MIN_GOOD_YEARS
    tree_drop = enough and bool(tree.get("persistent_change")) and (tree.get("change") or 0) < 0
    classes = land_classes(case) if case else []
    out: list[RuleResult] = []

    if heavy:
        out.append(
            _finding(
                "water_dry_season",
                Status.warn,
                "শুকনো মৌসুমেও আশেপাশে পানি",
                f"{_years_bn(heavy)} সালের ফেব্রুয়ারিতে (শুকনো মৌসুম) প্লটের আশেপাশের অনেকটা "
                "জায়গায় পানি দেখা গেছে। শুকনো মৌসুমে পানি থাকলে জায়গাটি নিচু, জলাবদ্ধ বা পুকুর/খাল "
                "হতে পারে।",
                "শুকনো ও বর্ষা দুই মৌসুমে নিজে বা আমিন দিয়ে জমিতে গিয়ে দেখুন পানি জমে কি না, "
                "আর আশেপাশের লোকজনের কাছে জিজ্ঞেস করুন।",
                buffer_m,
                {"years": heavy},
            )
        )
    if spikes:
        out.append(
            _finding(
                "water_spike",
                Status.warn,
                "কোনো এক বছরে হঠাৎ বেশি পানি",
                f"{_years_bn(spikes)} সালে প্লটের আশেপাশে অন্য বছরের চেয়ে অনেক বেশি পানি দেখা গেছে। "
                "এটি বন্যা, জলাবদ্ধতা বা নতুন পুকুর কাটার চিহ্ন হতে পারে।",
                f"{_years_bn(spikes)} সালে সেখানে কী হয়েছিল (বন্যা, জলাবদ্ধতা, পুকুর কাটা) "
                "স্থানীয়দের কাছে জেনে নিন।",
                buffer_m,
                {"years": spikes},
            )
        )
    if tree_drop:
        out.append(
            _finding(
                "tree_loss",
                Status.warn,
                "আশেপাশে গাছ কমেছে",
                f"প্লটের আশেপাশে গাছে ঢাকা জায়গা {_num_bn(tree['from'])}% থেকে "
                f"{_num_bn(tree['to'])}% হয়েছে ({to_bangla_digits(str(tree['from_year']))}–"
                f"{to_bangla_digits(str(tree['to_year']))}), এবং শেষের বছরগুলোতেও কম রয়েছে।",
                "জমিতে গিয়ে দেখুন গাছ কাটা হয়েছে কি না, এবং আশেপাশে নতুন ঘর, রাস্তা বা মাটি ভরাট হয়েছে কি না।",
                buffer_m,
                {"from": tree["from"], "to": tree["to"], "change": tree["change"]},
            )
        )
    agri = [c for c in classes if is_agricultural(c)]
    if agri and heavy:
        out.append(
            _finding(
                "class_water_mismatch",
                Status.warn,
                "কাগজে চাষের জমি, ছবিতে পানি",
                f"খতিয়ানে জমির শ্রেণী '{agri[0]}' (চাষের জমি), কিন্তু শুকনো মৌসুমেও "
                "আশেপাশে পানি দেখা গেছে। কাগজ আর মাঠের অবস্থা মিলছে কি না দেখা দরকার।",
                "মাঠে গিয়ে জমির আসল অবস্থা দেখুন, এবং ভূমি অফিসে খতিয়ানে লেখা শ্রেণী যাচাই করুন।",
                buffer_m,
                {"land_class": agri[0], "years": heavy},
            )
        )
    orchard = [c for c in classes if is_orchard(c)]
    if orchard and tree_drop:
        out.append(
            _finding(
                "class_tree_mismatch",
                Status.warn,
                "কাগজে বাগান, ছবিতে গাছ কমেছে",
                f"খতিয়ানে জমির শ্রেণী '{orchard[0]}', কিন্তু আশেপাশে গাছে ঢাকা জায়গা স্থায়ীভাবে "
                "কমেছে। কাগজ আর মাঠের অবস্থা মিলছে কি না দেখা দরকার।",
                "মাঠে গিয়ে দেখুন বাগান এখনো আছে কি না, এবং ভূমি অফিসে খতিয়ানে লেখা শ্রেণী যাচাই করুন।",
                buffer_m,
                {"land_class": orchard[0], "change": tree["change"]},
            )
        )
    if not enough:
        out.append(
            _finding(
                "insufficient_evidence",
                Status.skipped,
                "স্যাটেলাইট প্রমাণ যথেষ্ট নয়",
                f"পরিষ্কার ছবি পাওয়া গেছে মাত্র {to_bangla_digits(str(len(good)))}টি বছরের "
                f"(দরকার অন্তত {to_bangla_digits(str(MIN_GOOD_YEARS))}টি)। তাই বছরে বছরে "
                "পরিবর্তন নিয়ে কিছু বলা যাচ্ছে না। এটি কোনো পাস নয়।",
                "পরে আবার স্যাটেলাইট যাচাই চালান; ততক্ষণ নিজে জমিতে গিয়ে অবস্থা দেখুন।",
                buffer_m,
                {"good_years": good},
            )
        )
    return out
