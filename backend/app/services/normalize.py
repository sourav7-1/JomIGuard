"""Fill the derived ("normalize") fields of extracted documents. Spec: docs/specs/fields.md.

normalize_document(doc) -> NormalizeResult(doc, warnings). The input is never changed and
extractor fields are copied as they are; every derived field is recomputed (normalize is the
source of truth). Decimal throughout, never float, no rounding.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.schemas.extracted import DeedData, ExtractedDocument, HeirCertData, Owner, Plot

MESSAGES_BN = {
    "unsupported_unit": "জমির পরিমাণ এমন এককে লেখা যা app রূপান্তর করে না (বিঘা, কাঠা, আনা …)।",
    "missing_unit": "জমির পরিমাণের কোনো একক পড়া যায়নি, ঘরে বা কলামের শিরোনামে।",
    "unparseable_number": "সংখ্যাটি পড়া যায়নি।",
    "unparseable_date": "তারিখটি পড়া যায়নি।",
}


@dataclass(frozen=True)
class NormalizeWarning:
    code: str  # a key of MESSAGES_BN
    field_path: str  # the printed text field, e.g. "plots[0].area_text"
    message_bn: str


@dataclass
class NormalizeResult:
    doc: ExtractedDocument
    warnings: list[NormalizeWarning] = field(default_factory=list)


# --- text and digits ---

_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍﻿"))
_TO_ASCII = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
_TO_BN = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
_NUMBER = re.compile(r"\d+(?:\.\d+)?|\.\d+")


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def clean(s: str) -> str:
    """NFC without zero-width characters (ZWJ, ZWNJ, ZWSP, BOM): for matching only."""
    return nfc(s).translate(_ZERO_WIDTH)


def to_ascii_digits(s: str) -> str:
    return s.translate(_TO_ASCII)


def to_bangla_digits(s: str) -> str:
    return s.translate(_TO_BN)


def normalize_identifier(text: str) -> str:
    """ "নং: ৩০৫ / ১" -> "305/1". Stays a string; "/" is kept."""
    t = to_ascii_digits(clean(text)).strip()
    t = re.sub(nfc(r"^নং\s*[:ঃ]?|নং\s*[:ঃ]?$"), "", t)
    return re.sub(r"\s+", "", t)


def parse_decimal_text(text: str) -> Decimal | None:
    """ ".৪০০" -> Decimal("0.400"); "১.০০০", "০.৪০০", "১৫" work. None if not one plain number."""
    t = to_ascii_digits(clean(text)).strip()
    return Decimal(t) if _NUMBER.fullmatch(t) else None


def parse_money(text: str) -> Decimal | None:
    """ "৬০,০০,০০০/- টাকা" -> Decimal("6000000") (any digit grouping, "/-", "টাকা", "৳")."""
    t = to_ascii_digits(clean(text))
    t = re.sub(nfc(r"/-|টাকা|৳|\btk\b\.?"), "", t, flags=re.IGNORECASE)
    return parse_decimal_text(t.replace(",", ""))


# --- areas and shares ---

# shatangsho per unit; 1 একর = 100 শতাংশ (fields.md)
_UNITS = {nfc(u): Decimal(f) for u, f in {
    "একর": 100, "শতাংশ": 1, "শতক": 1, "ডেসিমেল": 1, "decimal": 1,
}.items()}  # fmt: skip
# never converted (Decision 2): local sizes vary, so a conversion would be a guess
_UNSUPPORTED = tuple(nfc(u) for u in ("বিঘা", "কাঠা", "গণ্ডা", "ছটাক", "আনা", "কড়া", "ক্রান্তি"))


def _unit(text: str) -> Decimal | str | None:
    """Factor of the unit in `text`, "unsupported" for a unit we do not convert, None if none."""
    t = clean(text).lower()
    if any(u in t for u in _UNSUPPORTED):
        return "unsupported"
    # several units ("১ একর ৫০ শতাংশ") also print several numbers: unparseable_number later
    return next((f for u, f in _UNITS.items() if u in t), None)


def _one_number(text: str) -> Decimal | None:
    numbers = _NUMBER.findall(to_ascii_digits(clean(text)).replace(",", ""))
    return Decimal(numbers[0]) if len(numbers) == 1 else None


def parse_area(text: str, unit_hint: str | None = None) -> tuple[Decimal | None, str | None]:
    """-> (shatangsho, warning code). Unit from the text first, else from unit_hint
    (the column header, area_unit_text), else missing_unit (Decision 8)."""
    unit = _unit(text)
    if unit is None and unit_hint:
        unit = _unit(unit_hint)
    if unit is None:
        return None, "missing_unit"
    if unit == "unsupported":
        return None, "unsupported_unit"
    number = _one_number(text)
    return (None, "unparseable_number") if number is None else (number * unit, None)


def parse_share(text: str) -> tuple[Decimal | None, str | None]:
    """ ".৪০০" -> (Decimal("0.400"), None): a fraction 0-1 of the khatian/plot.
    A share in আনা etc. -> (None, "unsupported_unit")."""
    if any(u in clean(text) for u in _UNSUPPORTED):
        return None, "unsupported_unit"
    number = _one_number(text)
    if number is None or number > 1:
        return None, "unparseable_number"
    return number, None


# --- names and dates ---

_HONORIFIC = re.compile(
    nfc(
        r"(?<!\S)(?:মোহা|মোছা|মোসা|মো)[ঃ:]\s*"  # glued forms too: "মোঃরহিম"
        r"|(?<!\S)(?:মোসাম্মৎ|মরহুমা|মরহুম|মৃত|শেখ)[.:ঃ]?(?=\s|$)"
    )
)
_END_PUNCT = " \t.,;:ঃ-–—()'\"।"


def normalize_name(name: str) -> str:
    """ "মোঃ রহিম উদ্দিন" -> "রহিম উদ্দিন". Removes honorifics and deceased markers only;
    full names like মোহাম্মদ stay."""
    t = _HONORIFIC.sub(" ", clean(name))
    return " ".join(t.split()).strip(_END_PUNCT)


def parse_date(text: str) -> tuple[date | None, str | None]:
    """ "১৫/০৩/২০১৮" -> 2018-03-15 (day/month/year). Year only or বঙ্গাব্দ -> (None, None):
    keep the text (fields.md). Anything else unreadable -> (None, "unparseable_date")."""
    t = to_ascii_digits(clean(text)).strip()
    if nfc("বঙ্গাব্দ") in t or nfc("বাং") in t or re.fullmatch(r"\D*\d{4}\D*", t):
        return None, None
    if m := re.fullmatch(r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})", t):
        d, mo, y = map(int, m.groups())
    elif m := re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", t):
        y, mo, d = map(int, m.groups())
    else:
        return None, "unparseable_date"
    try:
        return date(y, mo, d), None
    except ValueError:
        return None, "unparseable_date"


# --- documents ---


class _Run:
    def __init__(self) -> None:
        self.warnings: list[NormalizeWarning] = []

    def warn(self, code: str | None, path: str) -> None:
        if code:
            self.warnings.append(NormalizeWarning(code, path, MESSAGES_BN[code]))

    def area(self, text: str | None, hint: str | None, path: str) -> Decimal | None:
        if text is None:
            return None
        value, code = parse_area(text, hint)
        self.warn(code, path)
        return value

    def share(self, text: str | None, path: str) -> Decimal | None:
        if text is None:
            return None
        value, code = parse_share(text)
        self.warn(code, path)
        return value

    def plots(self, plots: list[Plot], hint: str | None, path: str) -> None:
        for i, p in enumerate(plots):
            at = f"{path}[{i}]"
            p.plot_total_area_shatangsho = self.area(
                p.plot_total_area_text, hint, f"{at}.plot_total_area_text"
            )
            p.khatian_share_fraction = self.share(p.khatian_share_text, f"{at}.khatian_share_text")
            p.area_shatangsho = self.area(p.area_text, hint, f"{at}.area_text")

    def owners(self, owners: list[Owner], total: Decimal | None, path: str) -> None:
        for i, o in enumerate(owners):
            o.name_normalized = normalize_name(o.name)
            o.share_fraction = self.share(o.share_text, f"{path}[{i}].share_text")
            o.share_shatangsho = (
                o.share_fraction * total
                if o.share_fraction is not None and total is not None
                else None
            )

    def date_text(self, text: str | None, path: str) -> None:
        if text is not None:
            self.warn(parse_date(text)[1], path)


def normalize_document(doc: ExtractedDocument) -> NormalizeResult:
    out = doc.model_copy(deep=True)
    run = _Run()
    if isinstance(out, HeirCertData):
        for i, h in enumerate(out.heirs):
            h.name_normalized = normalize_name(h.name)
            h.share_fraction = run.share(h.share_text, f"heirs[{i}].share_text")
        run.date_text(out.date_of_death_text, "date_of_death_text")
    elif isinstance(out, DeedData):
        run.plots(out.schedule_plots, None, "schedule_plots")
        out.transferred_area_shatangsho = run.area(
            out.transferred_area_text, None, "transferred_area_text"
        )
        # a deed has no khatian total, so no share_shatangsho
        run.owners(out.sellers, None, "sellers")
        run.owners(out.buyers, None, "buyers")
        run.date_text(out.registration_date_text, "registration_date_text")
    else:  # khatian or mutation: same area columns
        hint = out.area_unit_text
        run.plots(out.plots, hint, "plots")
        out.total_area_shatangsho = run.area(out.total_area_text, hint, "total_area_text")
        total = out.total_area_shatangsho
        if total is None and out.plots and all(p.area_shatangsho is not None for p in out.plots):
            total = sum((p.area_shatangsho for p in out.plots), Decimal(0))
        run.owners(out.owners, total, "owners")
        if out.doc_type == "khatian":
            run.date_text(out.record_date_text, "record_date_text")
        else:
            run.date_text(out.order_date_text, "order_date_text")
    return NormalizeResult(out, run.warnings)
