"""Baseline extractor: Tesseract OCR + regex/keyword rules per document type (cost 0).

OCR uses the Day 14 settings (preprocess gray, best Bangla model, psm 3) with a psm 6 fallback
when psm 3 reads almost nothing (it can miss photographed tables; see classify.py). Parsing is
line-based: header fields by "label: value" regexes, owners/heirs/plots from table rows.
Best effort and time-boxed: anything not found stays null, or "" for required text fields.
Values are copied as printed, except OCR repair of a lost leading "." in share/area cells
(".২৫০" read as "২৫০": a share or acre value of 250 is impossible). Identifiers get ASCII digits.
"""

import re
from collections.abc import Callable
from time import perf_counter

from pydantic import ValidationError

from app.services.extraction.base import MODELS, ExtractionMeta, ExtractionResult
from app.services.normalize import clean, normalize_identifier, parse_date, parse_money
from app.services.ocr import ocr
from app.services.preprocess import PreprocessError, preprocess

NAME = "tesseract_regex"
PSM, FALLBACK_PSM = 3, 6
MIN_TEXT = 200  # chars; less means psm 3 missed the page layout

D = "[০-৯0-9]"
ID = rf"{D}+(?:/{D}+)?"
NUM = rf"[.।]?{D}+(?:\.{D}+)?"
DATE = rf"{D}{{1,2}}/{D}{{1,2}}/{D}{{4}}"
SEP = r"\s*[:ঃ\-]?\s*"
SURVEYS = {"সি.এস.": "CS", "এস.এ.": "SA", "আর.এস.": "RS", "বি.এস.": "BS"}
DEED_TYPES = {"সাফ কবলা": "saf_kabala", "হেবা": "heba", "দান": "dan", "বণ্টন": "bonton",
              "বায়না": "bayna"}  # fmt: skip
RELATIONS = {"পুত্র": "son", "কন্যা": "daughter", "স্ত্রী": "wife", "স্বামী": "husband",
             "পিতা": "father", "মাতা": "mother", "ভাই": "brother", "বোন": "sister"}  # fmt: skip
MARKERS = {"পিং": "father", "পিতা": "father", "জং": "husband", "স্বামী": "husband"}


# --- small helpers ---


def find(pattern: str, text: str, group: int = 1) -> str | None:
    m = re.search(pattern, text, re.MULTILINE)
    return m.group(group).strip() if m else None


def ident(pattern: str, text: str) -> str | None:
    v = find(pattern, text)
    return normalize_identifier(v) if v else None


def word(label: str, text: str) -> str | None:
    """First word after a label ("জেলা: বরিশাল" -> "বরিশাল")."""
    return find(rf"{label}{SEP}([^\s,:ঃ]+)", text)


def restore_dot(cell: str) -> str:
    """OCR repair: ".২৫০" read as "২৫০" (no share or acre value is a 3+ digit integer)."""
    cell = cell.replace("।", ".")
    return f".{cell}" if "." not in cell and len(cell) >= 3 else cell


def date_of(text: str | None):
    return parse_date(text)[0] if text else None


def between(lines: list[str], start: Callable[[str], bool], stop: Callable[[str], bool]):
    out, inside = [], False
    for line in lines:
        if inside and stop(line):
            break
        if inside:
            out.append(line)
        elif start(line):
            inside = True
    return out


# --- tables ---


def owners_from(lines: list[str]) -> list[dict]:
    """Owner rows "<serial> <name> <share>", then "পিং-/জং- <name>" and "সাং- <place>" lines."""
    rows = between(
        lines,
        lambda s: "মালিক" in s and "নাম" in s,
        lambda s: ("দাগ" in s and "শ্রেণী" in s) or "দাগনং" in s,
    )
    owners: list[dict] = []
    for line in rows:
        if m := re.match(rf"^\S{{1,3}}\s+(.+?)\s+({NUM})$", line):
            owners.append({"name": m.group(1), "share_text": restore_dot(m.group(2))})
        elif owners and (m := re.match(r"^(পিং|জং|পিতা|স্বামী)\s*-\s*(.+)$", line)):
            owners[-1]["relation_marker"] = MARKERS[m.group(1)]
            owners[-1]["father_or_husband_name"] = m.group(2).strip()
        elif owners and line.startswith("সাং"):
            owners[-1]["address_text"] = line
    return owners


def plots_from(lines: list[str]) -> list[dict]:
    """Plot rows "<dag> <class> <plot total> <khatian share> <area>"."""
    rows = between(
        lines,
        lambda s: ("দাগ" in s and "শ্রেণী" in s) or "দাগনং" in s,
        lambda s: s.startswith("মোট জমি"),
    )
    plots = []
    for line in rows:
        if m := re.match(rf"^({ID})\s+(\S+)\s+({NUM})\s+({NUM})\s+({NUM})$", line):
            plots.append(
                {
                    "dag_no": normalize_identifier(m.group(1)),
                    "land_class": m.group(2),
                    "plot_total_area_text": restore_dot(m.group(3)),
                    "khatian_share_text": restore_dot(m.group(4)),
                    "area_text": restore_dot(m.group(5)),
                }
            )
    return plots


def location(text: str) -> dict:
    return {
        "district": word("জেলা", text) or "",
        "upazila": word(r"(?:থানা?/উপজেলা|উপজেলা(?: / থানা)?)", text) or "",
        "mouza": word("মৌজা", text) or "",
        "jl_no": ident(rf"জে\.?এল\.?\s*নং{SEP}({ID})", text),
    }


def land_record(text: str, lines: list[str]) -> dict:
    """Fields shared by a khatian and a mutation khatian."""
    total = find(rf"^মোট জমি\s*({NUM})", text)
    return {
        "location": location(text),
        "owners": owners_from(lines),
        "plots": plots_from(lines),
        "area_unit_text": "একর" if "(একর)" in text else None,
        "total_area_text": restore_dot(total) if total else None,
    }


# --- documents ---


def parse_khatian(text: str, lines: list[str]) -> dict:
    survey = find(r"(সি\.এস\.|এস\.এ\.|আর\.এস\.|বি\.এস\.)\s*খতিয়ান", text)
    return {
        "survey_type": SURVEYS.get(survey or "", "BS"),  # required enum: BS if unreadable
        "khatian_no": ident(rf"খতিয়ান নং{SEP}({ID})", text) or "",
        "touzi_no": ident(rf"তৌজি নং{SEP}({ID})", text),
        "landlord_name": find(rf"জমিদার{SEP}(.+)$", text),
        "annual_revenue_text": find(rf"বার্ষিক খাজনা{SEP}(.+)$", text),
        **land_record(text, lines),
    }


def parse_mutation(text: str, lines: list[str]) -> dict:
    order_text = find(rf"আদেশের তারিখ{SEP}({DATE})", text)
    fee = find(r"ফি[:ঃ]\s*([^\n]+?টাকা)", text)
    return {
        "case_no": ident(rf"মোকদ্দম\S*\s*নং{SEP}({ID})", text) or "",
        "office": find(r"^(.*সহকারী কমিশনার.*)$", text),
        "order_date_text": order_text,
        "order_date": date_of(order_text),
        "dcr_no": ident(rf"ডি\.সি\.আ\S*\s*নং{SEP}({ID})", text),
        "fee_taka": parse_money(fee) if fee else None,
        "old_khatian_no": ident(rf"পূর্বের খতিয়ান[^:ঃ\n]*[:ঃ]\s*({ID})", text),
        "new_khatian_no": ident(rf"(?<!পূর্বের )খতিয়ান নং{SEP}({ID})", text) or "",
        "holding_no": ident(rf"হো\S*\s*নং{SEP}({ID})", text),
        "basis_text": find(rf"নামজারির কারণ{SEP}(.+)$", text),
        **land_record(text, lines),
    }


def party(line: str) -> dict:
    """ "নাম, পিতা- X, সাং- Y, উপজেলা- Z, জেলা- W" -> Owner fields."""
    parts = [p.strip() for p in line.split(",")]
    out = {"name": parts[0]}
    for i, p in enumerate(parts[1:], 1):
        if m := re.match(r"^(পিতা|স্বামী)\s*-\s*(.+)$", p):
            out["father_or_husband_name"] = m.group(2)
            out["relation_marker"] = MARKERS[m.group(1)]
        elif p.startswith("সাং"):
            out["address_text"] = ", ".join(parts[i:])
            break
    return out


def parse_deed(text: str, lines: list[str]) -> dict:
    deed_no = ident(rf"(?<!বায়া )দলিল নং[:ঃ]\s*({ID})", text)
    reg_text = find(rf"রে\S*স্ট্রির তারিখ{SEP}({DATE})", text)
    sellers = between(lines, lambda s: s.startswith("দাতা /"), lambda s: "গ্রহীতা /" in s)
    buyers = between(lines, lambda s: s.startswith("গ্রহীতা /"), lambda s: "মালিকানার" in s)
    schedule = "\n".join(between(lines, lambda s: s.strip() == "তফসিল", lambda s: "সাক্ষী" in s))
    refs = [
        {"survey_type": SURVEYS[s], "khatian_no": normalize_identifier(n)}
        for s, n in re.findall(rf"(সি\.এস\.|এস\.এ\.|আর\.এস\.|বি\.এস\.)\s*({ID})", schedule)
    ]
    area = find(r"হস্ত\S*\s+জমির পরিমাণ\s*(.+)$", schedule) or ""
    dag = ident(rf"দাগ নং\s*({ID})", schedule)
    price = find(r"মূল্য[:ঃ]?\s*([^\n]+?টাকা)", text)
    prior = find(r"বায়া দলিল নং\s*([^)]+)\)", text) or ""
    deed_type = next((v for k, v in DEED_TYPES.items() if k in text[:300]), "other")
    seller_line = next((s for s in sellers if "," in s), None)
    return {
        "deed_type": deed_type,
        "is_draft": "খসড়া" in text or deed_no is None,
        "deed_no": deed_no,
        "deed_year": ident(rf"সন{SEP}({D}{{4}})", text),
        "registration_date_text": reg_text,
        "registration_date": date_of(reg_text),
        "sub_registry_office": word("সাব-রেজিস্ট্রি অফিস", text),
        "book_no": ident(rf"বহি\s*নং{SEP}({ID})", text),
        "sellers": [party(seller_line)] if seller_line else [],
        "buyers": [party(b) for b in buyers if "," in b],
        "price_text": price,
        "price_taka": parse_money(price) if price else None,
        "schedule_location": location(schedule),
        "schedule_khatians": refs,
        "schedule_plots": (
            [
                {
                    "dag_no": dag,
                    "land_class": find(rf"দাগ নং\s*{ID}\s*\(([^)]+)\)", schedule),
                    "area_text": area,
                }
            ]
            if dag
            else []
        ),
        "transferred_area_text": area,
        "prior_deeds": [
            {"deed_no": normalize_identifier(n), "deed_year": normalize_identifier(y)}
            for n, y in re.findall(rf"({D}+)/({D}{{4}})", prior)
        ],
        "title_source_text": find(r"((?:ওয়ারিশ|ক্রয়|দান|হেবা) সূত্রে প্রাপ্ত)", text),
    }


def parse_heir_cert(text: str, lines: list[str]) -> dict:
    issue_text = find(rf"স্মারক নং.*?তারিখ{SEP}({DATE})", text)
    death_text = find(rf"গত\s+({DATE})\s+তারিখে", text)
    sentence = find(r"(মরহুম[^।]*)", text) or ""
    rows = between(lines, lambda s: "ওয়ারিশের নাম" in s, lambda s: s.startswith("আমার জানামতে"))
    heirs = []
    for line in rows:
        if m := re.match(r"^\S{1,3}\s+(.+)\s+(\S+)$", line):
            rel = RELATIONS.get(m.group(2))
            heirs.append(
                {
                    "name": m.group(1) if rel else f"{m.group(1)} {m.group(2)}",
                    "relation": rel or "other",
                    "relation_text": m.group(2) if rel else "",
                }
            )
    title = next((t for t in ("চেয়ারম্যান", "মেয়র", "কাউন্সিলর") if t in text), None)
    return {
        "certificate_no": ident(rf"স্মারক নং{SEP}({ID})", text),
        "issue_date": date_of(issue_text),
        "issuing_authority": lines[0] if lines else "",
        "issuer_title": title,
        "deceased_name": find(r"মরহুম\s+([^,]+)", sentence) or "",
        "deceased_father_or_husband_name": find(r"^[^,]+,\s*(?:পিতা|স্বামী)\s*-\s*([^,]+)", sentence),
        "deceased_address": {
            "district": word("জেলা", sentence),
            "upazila": word("উপজেলা", sentence),
            "address_text": find(r"(গ্রাম\s*-\s*[^,]+)", sentence),
        },
        "date_of_death_text": death_text,
        "date_of_death": date_of(death_text),
        "heirs": heirs,
    }


PARSERS = {"khatian": parse_khatian, "deed": parse_deed, "dcr": parse_mutation,
           "heir_cert": parse_heir_cert}  # fmt: skip


def parse(text: str, doc_type: str):
    """OCR text -> validated document (pydantic model). Raises ValidationError if invalid."""
    t = clean(text)
    lines = [" ".join(s.split()) for s in t.splitlines() if s.strip()]
    data = {"doc_type": doc_type, **PARSERS[doc_type](t, lines)}
    return MODELS[doc_type].model_validate(data)


class TesseractRegexExtractor:
    model = NAME

    def extract(self, image_bytes: bytes, doc_type: str) -> ExtractionResult:
        start = perf_counter()
        meta = ExtractionMeta(model=NAME)

        def done(**kw) -> ExtractionResult:
            meta.latency_s = round(perf_counter() - start, 3)
            return ExtractionResult(meta=meta, **kw)

        if doc_type not in MODELS:
            return done(error=f"unknown doc_type {doc_type!r}")
        try:
            gray = preprocess(image_bytes).gray
        except PreprocessError as e:
            return done(error=f"image: {e}")
        text = ocr(gray, psm=PSM).text
        if len(text) < MIN_TEXT:
            text = ocr(gray, psm=FALLBACK_PSM).text
        try:
            return done(document=parse(text, doc_type))
        except ValidationError as e:
            return done(error=f"invalid output: {e.error_count()} errors")
