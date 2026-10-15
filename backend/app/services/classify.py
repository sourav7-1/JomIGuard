"""Document type from OCR text keywords: khatian, deed, dcr (mutation), heir_cert or other.

classify_text(text) scores each type by the weights of its keywords found in the text (exact,
or rapidfuzz partial ratio >= FUZZY_MIN for keywords long enough that one OCR error still leaves
them recognisable). Words shared by several land records (দাগ নং, খতিয়ান নং, মালিক ...) weigh
little; words only one type prints weigh a lot, so a mutation page (which carries a full khatian
table) still scores highest as dcr. "other" when the best score is low or the top two are close.
Weights and thresholds were tuned on the v2 TRAIN split (ml/eval/classify_eval.py).
"""

from collections.abc import Callable
from dataclasses import dataclass, field

from rapidfuzz import fuzz

from app.services.normalize import clean, nfc
from app.services.ocr import ocr
from app.services.preprocess import preprocess

DOC_TYPES = ("khatian", "deed", "dcr", "heir_cert")
FUZZY_MIN = 85
FUZZY_MIN_LEN = 5  # shorter keywords must match exactly: one wrong letter changes the word
MIN_SCORE = 4.0  # best type needs at least this much keyword weight
MIN_CONFIDENCE = 0.4  # (best - second) / best below this: too close to call
PSM = 3  # the OCR default (data/preview/ocr/grid.md)
# psm 3 layout analysis sometimes finds only the footer on a photographed table (khatian,
# medium/heavy presets); sparse-text mode still reads the words. Used only when psm 3 gives "other".
FALLBACK_PSM = 11

KEYWORDS: dict[str, dict[str, float]] = {
    "khatian": {
        "খতিয়ান": 1,
        "জরিপ": 1,
        "দাগ নং": 0.5,
        "মালিক": 0.5,
        "অংশ": 0.5,
        "জে.এল": 0.5,
        # printed only on a khatian (a mutation khatian has none of these); the survey title
        # "আর.এস. খতিয়ান" / "এস.এ. খতিয়ান" is the only one an RS/BS khatian always prints
        "এস. খতিয়ান": 3,
        "এস.এ. খতিয়ান": 3,
        "তৌজি": 3,
        "রেভিনিউ": 3,
        "জমিদার": 3,
        "অংশীদার": 3,
        "বার্ষিক খাজনা": 3,
    },
    "deed": {
        "দলিল": 2,
        "দাতা": 2,
        "গ্রহীতা": 3,
        "তফসিল": 3,
        "সাব-রেজিস্ট্রি": 3,
        "রেজিস্ট্রির তারিখ": 2,
        "কবলা": 2,
        "সাক্ষী": 2,
        "বিক্রেতা": 2,
        "হস্তান্তর": 2,
        "বায়া দলিল": 2,
    },
    "dcr": {
        "নামজারি": 4,
        "জমাভাগ": 3,
        "ডি.সি.আর": 4,
        "সহকারী কমিশনার (ভূমি)": 3,
        "মোকদ্দমা": 3,
        "কার্বন রসিদ": 3,
        "হোল্ডিং নং": 2,
        "পূর্বের খতিয়ান": 2,
        "আদেশের তারিখ": 2,
    },
    "heir_cert": {
        "ওয়ারিশ": 3,
        "সনদ": 2,
        "ইউনিয়ন পরিষদ": 2,
        "পৌরসভা": 2,
        "মৃত": 1,
        "মরহুম": 2,
        "চেয়ারম্যান": 2,
        "প্রত্যয়ন": 3,
        "সম্পর্ক": 1,
    },
}
_KEYWORDS = {t: {nfc(k): w for k, w in kws.items()} for t, kws in KEYWORDS.items()}

LABEL_BN = {
    "khatian": "খতিয়ান",
    "deed": "দলিল",
    "dcr": "নামজারি খতিয়ান / ডি.সি.আর.",
    "heir_cert": "ওয়ারিশ সনদ",
}


@dataclass
class ClassifyResult:
    doc_type: str  # one of DOC_TYPES or "other"
    confidence: float  # 0-1
    scores: dict[str, float] = field(default_factory=dict)
    matched_keywords: dict[str, list[str]] = field(default_factory=dict)


@dataclass(frozen=True)
class LabelWarning:
    code: str  # "doc_type_mismatch" | "doc_type_unclear"
    message_bn: str


def _found(keyword: str, text: str) -> bool:
    if keyword in text:
        return True
    return len(keyword) >= FUZZY_MIN_LEN and fuzz.partial_ratio(keyword, text) >= FUZZY_MIN


def classify_text(text: str) -> ClassifyResult:
    t = " ".join(clean(text or "").split())
    matched = {d: [k for k in _KEYWORDS[d] if _found(k, t)] for d in DOC_TYPES}
    scores = {d: float(sum(_KEYWORDS[d][k] for k in matched[d])) for d in DOC_TYPES}
    ranked = sorted(DOC_TYPES, key=lambda d: scores[d], reverse=True)
    best, second = scores[ranked[0]], scores[ranked[1]]
    margin = (best - second) / best if best else 0.0
    confidence = round(margin * min(1.0, best / MIN_SCORE), 3)
    doc_type = ranked[0] if best >= MIN_SCORE and margin >= MIN_CONFIDENCE else "other"
    return ClassifyResult(doc_type, confidence, scores, matched)


def classify_ocr(read_text: Callable[[int], str]) -> ClassifyResult:
    """read_text(psm) -> OCR text. psm 3 first; psm 11 only if that gives "other"."""
    result = classify_text(read_text(PSM))
    if result.doc_type == "other":
        fallback = classify_text(read_text(FALLBACK_PSM))
        if fallback.doc_type != "other":
            return fallback
    return result


def classify_image(image_bytes: bytes) -> ClassifyResult:
    gray = preprocess(image_bytes).gray
    return classify_ocr(lambda psm: ocr(gray, psm=psm).text)


def check_user_label(user_doc_type: str, result: ClassifyResult) -> LabelWarning | None:
    """None if the image looks like the type the user chose; otherwise a warning in Bangla."""
    if result.doc_type == user_doc_type:
        return None
    chosen = LABEL_BN.get(user_doc_type, user_doc_type)
    if result.doc_type == "other":
        return LabelWarning(
            "doc_type_unclear",
            f"ছবিটি {chosen} কিনা নিশ্চিত হওয়া যায়নি। সঠিক কাগজ ও পরিষ্কার ছবি দিয়েছেন কিনা দেখে নিন।",
        )
    return LabelWarning(
        "doc_type_mismatch",
        f"আপনি {chosen} বেছে নিয়েছেন, কিন্তু ছবিটি দেখে {LABEL_BN[result.doc_type]} মনে হচ্ছে। "
        "সঠিক কাগজ দিয়েছেন কিনা দেখে নিন।",
    )
