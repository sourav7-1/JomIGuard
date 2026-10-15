import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from app.schemas.extracted import ExtractedDocument
from app.services.normalize import (
    normalize_document,
    normalize_identifier,
    normalize_name,
    parse_area,
    parse_date,
    parse_decimal_text,
    parse_money,
    parse_share,
    to_ascii_digits,
    to_bangla_digits,
)

TESTS = Path(__file__).parents[1]
SAMPLES = sorted((TESTS / "fixtures/samples").glob("*.json"))
SCENARIO_DOCS = sorted(
    p for p in (TESTS / "scenarios").glob("*/*.json") if p.name != "expected.json"
)
DERIVED = {
    "name_normalized",
    "share_fraction",
    "share_shatangsho",
    "plot_total_area_shatangsho",
    "khatian_share_fraction",
    "area_shatangsho",
    "total_area_shatangsho",
    "transferred_area_shatangsho",
}
UNIT_CODES = {"unsupported_unit", "missing_unit"}
documents = TypeAdapter(ExtractedDocument)
ZWNJ = "‌"


def load(path: Path):
    return documents.validate_json(path.read_bytes())


def strip_derived(node):
    if isinstance(node, dict):
        return {k: None if k in DERIVED else strip_derived(v) for k, v in node.items()}
    if isinstance(node, list):
        return [strip_derived(v) for v in node]
    return node


def stripped(doc):
    return documents.validate_python(strip_derived(doc.model_dump()))


def codes(result) -> list[str]:
    return [w.code for w in result.warnings]


# --- digits and identifiers ---


def test_digits_both_ways():
    assert to_ascii_digits("৩০৫/১") == "305/1"
    assert to_bangla_digits("305/1") == "৩০৫/১"
    assert to_ascii_digits(to_bangla_digits("0123456789")) == "0123456789"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("৩০৫/১", "305/1"),
        ("৮৮২", "882"),
        ("নং ৩০৫", "305"),
        ("নং: ৮৮২", "882"),
        ("নংঃ ৮৮২", "882"),
        ("৫১২ / ১৮", "512/18"),
        ("৩০৫ নং", "305"),
    ],
)
def test_normalize_identifier(text, expected):
    assert normalize_identifier(text) == expected


# --- numbers and money ---


@pytest.mark.parametrize(
    ("text", "expected"),
    [(".৪০০", "0.400"), ("০.৪০০", "0.400"), ("১.০০০", "1.000"), (".১৫০০", "0.1500"), ("১৫", "15")],
)
def test_parse_decimal_text(text, expected):
    value = parse_decimal_text(text)
    assert isinstance(value, Decimal) and value == Decimal(expected)
    assert str(value) == expected  # exact digits kept, no float


def test_parse_decimal_text_rejects_non_numbers():
    assert parse_decimal_text("abc") is None
    assert parse_decimal_text("১.২.৩") is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [("৬০,০০,০০০/- টাকা", 6000000), ("১,১৫০/- টাকা", 1150), ("৳ ৫,০০০", 5000), ("৬০০০০০০", 6000000)],
)
def test_parse_money_indian_grouping(text, expected):
    assert parse_money(text) == Decimal(expected)


def test_parse_money_garbage_is_none():
    assert parse_money("ষাট লক্ষ টাকা") is None


# --- areas ---


@pytest.mark.parametrize(
    ("text", "hint", "expected"),
    [
        (".১৫০০ একর", None, "15"),
        ("১.৫ একর", None, "150"),
        ("১০ শতাংশ", None, "10"),
        ("৬.৫ শতাংশ", None, "6.5"),
        ("১০ শতক", None, "10"),
        ("১০ ডেসিমেল", None, "10"),
        ("10 decimal", None, "10"),
        (".১৫০০", "একর", "15"),  # no unit in the cell: the column header decides
        (".১৫০০", "জমির পরিমাণ (একর)", "15"),
        ("১০ শতাংশ", "একর", "10"),  # the cell's own unit wins over the header
    ],
)
def test_parse_area_supported_units(text, hint, expected):
    assert parse_area(text, hint) == (Decimal(expected), None)


@pytest.mark.parametrize("text", ["২ কাঠা", "১ বিঘা", "৩ গণ্ডা", "২ ছটাক", "।০ আনা", "১ কড়া"])
def test_parse_area_unsupported_units_never_guessed(text):
    assert parse_area(text) == (None, "unsupported_unit")
    assert parse_area(text, "একর") == (None, "unsupported_unit")


def test_parse_area_unsupported_unit_in_header():
    assert parse_area("৫", "বিঘা") == (None, "unsupported_unit")


def test_parse_area_missing_unit():
    assert parse_area(".১৫০০") == (None, "missing_unit")
    assert parse_area(".১৫০০", "") == (None, "missing_unit")


def test_parse_area_unparseable_number():
    assert parse_area("একর") == (None, "unparseable_number")
    assert parse_area("১ একর ৫০ শতাংশ") == (None, "unparseable_number")  # mixed: no guess


# --- shares ---


def test_parse_share():
    assert parse_share(".৪০০") == (Decimal("0.400"), None)
    assert parse_share("১.০০০") == (Decimal("1.000"), None)
    assert parse_share("।০ আনা") == (None, "unsupported_unit")
    assert parse_share("৮ আনা") == (None, "unsupported_unit")
    assert parse_share("অজানা")[0] is None


def test_owner_shatangsho_demo():
    # the demo: রহিম's share .৪০০ of a 15 শতাংশ khatian = 6 শতাংশ
    doc = load(TESTS / "fixtures/samples/khatian.json")
    result = normalize_document(stripped(doc))
    rahim = result.doc.owners[0]
    assert rahim.share_fraction == Decimal("0.400")
    assert rahim.share_shatangsho == Decimal("6")
    assert result.doc.total_area_shatangsho == Decimal("15")
    assert result.warnings == []


def test_owner_shatangsho_uses_plot_sum_when_total_missing():
    data = load(TESTS / "fixtures/samples/khatian.json").model_dump()
    data["total_area_text"] = None
    data["plots"].append({**data["plots"][0], "dag_no": "306", "area_text": ".০৫০০"})
    result = normalize_document(stripped(documents.validate_python(data)))
    assert result.doc.total_area_shatangsho is None
    assert result.doc.owners[0].share_shatangsho == Decimal("0.400") * Decimal("20")


def test_owner_shatangsho_is_exact_not_rounded():
    data = load(TESTS / "fixtures/samples/khatian.json").model_dump()
    data["owners"][0]["share_text"] = ".৩৩৪"
    data["total_area_text"] = ".০০০৭"  # 0.07 শতাংশ
    owner = normalize_document(documents.validate_python(data)).doc.owners[0]
    assert owner.share_shatangsho == Decimal("0.02338")


# --- names ---


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("মোঃ রহিম উদ্দিন", "রহিম উদ্দিন"),
        ("মো: রহিম উদ্দিন", "রহিম উদ্দিন"),
        ("মোঃরহিম উদ্দিন", "রহিম উদ্দিন"),
        ("মোহাঃ রহিম উদ্দিন", "রহিম উদ্দিন"),
        ("মোছাঃ সালমা খাতুন", "সালমা খাতুন"),
        ("মোসাঃ সালমা খাতুন", "সালমা খাতুন"),
        ("মোসাম্মৎ সালমা খাতুন", "সালমা খাতুন"),
        ("শেখ রহিম উদ্দিন", "রহিম উদ্দিন"),
        ("মরহুম রহমান", "রহমান"),
        ("মরহুমা আমেনা বেগম", "আমেনা বেগম"),
        ("মৃত রহমান", "রহমান"),
        ("  রহিম   উদ্দিন, ", "রহিম উদ্দিন"),
        ("মোহাম্মদ রহিম", "মোহাম্মদ রহিম"),  # a full name, not an honorific
        ("মোহাম্মদ শেখর", "মোহাম্মদ শেখর"),  # "শেখ" only as a whole word
    ],
)
def test_normalize_name(name, expected):
    assert normalize_name(name) == expected


def test_honorific_spellings_match():
    assert normalize_name("মোঃ রহিম উদ্দিন") == normalize_name("মো: রহিম উদ্দিন")


def test_zero_width_difference_still_equal():
    # ZWNJ inside a word changes the bytes, not the name
    assert normalize_name(f"রহিম উদ্{ZWNJ}দিন") == normalize_name("রহিম উদ্দিন")


def test_name_nfc():
    printed = "মোছাঃ সালমা খাতুন"
    decomposed = printed.replace("ো", "ো")  # ো as two code points
    assert decomposed != printed
    assert normalize_name(decomposed) == "সালমা খাতুন"


# --- dates ---


def test_parse_date():
    assert parse_date("১৫/০৩/২০১৮") == (date(2018, 3, 15), None)
    assert parse_date("০১-০২-২০১৮") == (date(2018, 2, 1), None)
    assert parse_date("2018-03-15") == (date(2018, 3, 15), None)


@pytest.mark.parametrize("text", ["১৯৮৫", "১৯৮৫ সাল", "১৫ বৈশাখ ১৩৯২ বঙ্গাব্দ", "১৩৯২ বাং"])
def test_parse_date_year_only_or_bangla_calendar_is_silent(text):
    assert parse_date(text) == (None, None)


@pytest.mark.parametrize("text", ["অস্পষ্ট", "৩১/০২/২০১৮", "১৫/০৩"])
def test_parse_date_garbage_warns(text):
    assert parse_date(text) == (None, "unparseable_date")


# --- documents ---


def test_document_warnings_have_path_and_bangla_message():
    data = load(TESTS / "scenarios/15_unsupported_unit_katha/deed.json")
    result = normalize_document(data)
    assert {(w.code, w.field_path) for w in result.warnings} == {
        ("unsupported_unit", "schedule_plots[0].area_text"),
        ("unsupported_unit", "transferred_area_text"),
    }
    assert all(w.message_bn for w in result.warnings)


def test_unparseable_date_text_warns_but_date_untouched():
    doc = load(TESTS / "fixtures/samples/heir_cert.json")
    doc.date_of_death_text = "অস্পষ্ট"
    result = normalize_document(doc)
    assert codes(result) == ["unparseable_date"]
    assert result.doc.date_of_death == doc.date_of_death


def test_derived_fields_recomputed_even_if_filled():
    doc = load(TESTS / "fixtures/samples/khatian.json")
    doc.owners[0].share_fraction = Decimal("0.9")
    doc.owners[0].name_normalized = "ভুল"
    owner = normalize_document(doc).doc.owners[0]
    assert owner.share_fraction == Decimal("0.400") and owner.name_normalized == "রহিম উদ্দিন"


@pytest.mark.parametrize("path", SAMPLES + SCENARIO_DOCS, ids=lambda p: str(p.relative_to(TESTS)))
def test_never_changes_extractor_fields_or_input(path):
    doc = load(path)
    before = doc.model_dump()
    result = normalize_document(doc)
    assert doc.model_dump() == before  # input untouched
    assert result.doc is not doc
    assert strip_derived(result.doc.model_dump()) == strip_derived(before)


# --- round trip: hand-filled derived values == normalize ---


def expected_unit_codes(path: Path) -> set[str]:
    expected = json.loads((path.parent / "expected.json").read_text(encoding="utf-8"))
    return {
        f["code"]
        for f in expected["expected_findings"]
        if f["code"] in UNIT_CODES and path.name in f["documents"]
    }


@pytest.mark.parametrize("path", SAMPLES + SCENARIO_DOCS, ids=lambda p: str(p.relative_to(TESTS)))
def test_round_trip(path):
    original = load(path)
    result = normalize_document(stripped(original))
    assert result.doc == original
    unit_codes = set(codes(result)) & UNIT_CODES
    if path in SCENARIO_DOCS:
        assert unit_codes == expected_unit_codes(path)
    else:
        assert unit_codes == set()
