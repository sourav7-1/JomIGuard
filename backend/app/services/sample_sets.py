# ruff: noqa: E501  (page templates: long Bangla lines read better unwrapped)
"""Synthetic sample documents for ONE case: the judge's own mouza, dag, khatian and upazila.

Each scenario starts from a hand-made answer-key case (copied from tests/scenarios into
app/scripts/demo_data/sample_sets/<A-D>), gets this land's location, and is rendered to a
watermarked PNG with Pillow (Bangla shaping via raqm). The expected result is what the real rule
engine says about that ground truth, i.e. the result if every field is read correctly.
"""

import json
import math
import random
import uuid
from dataclasses import dataclass
from functools import cache
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pydantic import TypeAdapter

from app.models import Land
from app.schemas.extracted import ExtractedDocument
from app.schemas.land_case import CaseDocumentInput
from app.services.land_case import build_land_case
from app.services.normalize import to_ascii_digits, to_bangla_digits
from app.services.risk import assess
from app.services.rules import run_rules

SETS_DIR = Path(__file__).resolve().parents[1] / "scripts" / "demo_data" / "sample_sets"
FONT = Path(__file__).resolve().parents[1] / "assets" / "fonts" / "NotoSansBengali.ttf"
SCENARIOS = ("A", "B", "C", "D", "E")
SOURCE = {"A": "A", "B": "B", "C": "C", "D": "D", "E": "A"}  # E: set A, handwritten-style deed
# the answer-key cases' location, replaced by the land's
OLD = {"district": "বরিশাল", "upazila": "গৌরনদী", "mouza": "চাঁদশী", "khatian": "882", "dag": "305"}
# Option B: one sample per document type, all from set A (B's prior deed for "prior_deed")
SINGLE = {
    "khatian": ("A", "khatian_bs"),
    "deed": ("A", "deed"),
    "prior_deed": ("B", "deed_prior_1985"),
    "dcr": ("A", "mutation"),
    "heir_cert": ("A", "heir_cert"),
}
_documents = TypeAdapter(ExtractedDocument)
README = """JomiGuard sample documents / নমুনা কাগজ
সব কাগজ কাল্পনিক, শুধু পরীক্ষার জন্য। All documents are synthetic and watermarked.
A = সব মিলেছে (all agree) · B = বিক্রেতা বেশি বিক্রি করছেন (sells more than share)
C = দাগ অমিল (dag mismatch) · D = ওয়ারিশ বাদ (heir missing from mutation)
E = হাতে লেখার মতো দলিল (handwritten-style deed)
Upload one folder into one case.
"""


@dataclass
class SampleFile:
    name: str  # file name, e.g. "2-deed.png"
    doc_type: str  # upload doc_type: khatian | deed | dcr | heir_cert
    data: dict  # the ground truth (what a perfect read returns)
    handwritten: bool = False


ORDER = {
    "khatian_bs": "1-khatian",
    "deed": "2-deed",
    "mutation": "3-mutation",
    "heir_cert": "4-heir-certificate",
    "deed_prior_1985": "5-previous-deed",
}


@cache
def _raw(source: str) -> dict[str, str]:
    return {
        p.stem: p.read_text(encoding="utf-8") for p in sorted((SETS_DIR / source).glob("*.json"))
    }


def _mismatch_dag(dag: str) -> str:
    return str(int(dag) + 1) if dag.isdigit() else f"{dag}1"


def localize(text: str, land: Land) -> dict:
    """Put the land's location into one answer-key document (text replace + identifier walk)."""
    for key in ("district", "upazila", "mouza"):
        new = (getattr(land, key) or "").strip()
        if new:
            text = text.replace(OLD[key], new)
    data = json.loads(text)
    dag = to_ascii_digits((land.dag_no or "").strip()) or OLD["dag"]
    khatian = to_ascii_digits((land.khatian_no or "").strip()) or OLD["khatian"]
    swap = {OLD["dag"]: dag, "306": _mismatch_dag(dag)}  # 306 = the dag-mismatch case's deed dag

    def walk(v, key=""):
        if isinstance(v, dict):
            return {k: walk(x, k) for k, x in v.items()}
        if isinstance(v, list):
            return [walk(x, key) for x in v]
        if key == "dag_no" and v in swap:
            return swap[v]
        if key in ("khatian_no", "new_khatian_no") and v == OLD["khatian"]:
            return khatian
        return v

    return walk(data)


def sample_set(land: Land, scenario: str) -> list[SampleFile]:
    out = []
    for stem, text in _raw(SOURCE[scenario]).items():
        data = localize(text, land)
        out.append(
            SampleFile(
                f"{ORDER[stem]}.png",
                data["doc_type"],
                data,
                handwritten=scenario == "E" and stem == "deed",
            )
        )
    return sorted(out, key=lambda f: f.name)


def single_sample(land: Land, kind: str) -> SampleFile:
    source, stem = SINGLE[kind]
    data = localize(_raw(source)[stem], land)
    return SampleFile(f"sample-{kind}.png", data["doc_type"], data)


def expected(files: list[SampleFile]) -> dict:
    """The rule engine on the ground truth: the result if every field is read correctly."""
    inputs = [
        CaseDocumentInput(source_id=f.name, data=_documents.validate_python(f.data)) for f in files
    ]
    case = build_land_case(inputs)
    run = run_rules(case)
    result = assess(case, run)
    return {
        "risk_level": result.risk_level,
        "headline_bn": result.headline_bn,
        "findings": [{"rule_id": f.rule_id, "title_bn": f.title_bn} for f in result.findings],
    }


# --- rendering ---------------------------------------------------------------------------

W, M = 1240, 70  # page width, margin
INK, MUTED, LINE = (20, 20, 20), (90, 90, 90), (60, 60, 60)
SURVEY = {"CS": "সি.এস.", "SA": "এস.এ.", "RS": "আর.এস.", "BS": "বি.এস.", "CITY": "সিটি জরিপ"}
DEED_LABEL = {
    "saf_kabala": "সাফ কবলা দলিল",
    "heba": "হেবা দলিল",
    "dan": "দানপত্র দলিল",
    "bonton": "বণ্টননামা দলিল",
    "bayna": "বায়নানামা দলিল",
    "other": "দলিল",
}
MARKER = {"father": "পিতা", "husband": "স্বামী"}


@cache
def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(str(FONT), size, layout_engine=ImageFont.Layout.RAQM)
    if bold:
        font.set_variation_by_axes([700])
    return font


bn = to_bangla_digits


class Page:
    """A tiny top-down layout: lines, wrapped paragraphs and bordered tables."""

    def __init__(self):
        self.img = Image.new("RGB", (W, 3200), "white")
        self.d = ImageDraw.Draw(self.img)
        self.y = M

    def text(self, s: str, size=24, bold=False, center=False, gap=10, color=INK):
        f = _font(size, bold)
        x = (W - self.d.textlength(s, font=f)) / 2 if center else M
        self.d.text((x, self.y), s, font=f, fill=color)
        self.y += int(size * 1.6) + gap

    def para(self, s: str, size=23):
        f, line = _font(size), ""
        for word in s.split():
            trial = f"{line} {word}".strip()
            if self.d.textlength(trial, font=f) > W - 2 * M and line:
                self.text(line, size, gap=2)
                line = word
            else:
                line = trial
        if line:
            self.text(line, size, gap=12)

    def pairs(self, items: list[tuple[str, str]], cols=2, size=23):
        f, fb = _font(size), _font(size, True)
        cw = (W - 2 * M) / cols
        for i, (k, v) in enumerate(items):
            x = M + (i % cols) * cw
            self.d.text((x, self.y), f"{k}: ", font=f, fill=INK)
            self.d.text((x + self.d.textlength(f"{k}: ", font=f), self.y), v, font=fb, fill=INK)
            if i % cols == cols - 1 or i == len(items) - 1:
                self.y += int(size * 1.7)
        self.y += 8

    def table(self, head: list[str], rows: list[list[str]], widths: list[float], size=22):
        f, fb = _font(size), _font(size, True)
        xs = [M]
        for w in widths:
            xs.append(xs[-1] + w * (W - 2 * M))

        def row(cells, font, shade=False):
            lines = [c.split("\n") for c in cells]
            h = max(len(c) for c in lines) * int(size * 1.5) + 16
            if shade:
                self.d.rectangle([M, self.y, W - M, self.y + h], fill=(242, 242, 242))
            for i, cell in enumerate(lines):
                for j, s in enumerate(cell):
                    self.d.text(
                        (xs[i] + 10, self.y + 8 + j * int(size * 1.5)), s, font=font, fill=INK
                    )
            for x in xs:
                self.d.line([x, self.y, x, self.y + h], fill=LINE, width=2)
            self.d.line([M, self.y, W - M, self.y], fill=LINE, width=2)
            self.y += h
            self.d.line([M, self.y, W - M, self.y], fill=LINE, width=2)

        row(head, fb, shade=True)
        for r in rows:
            row(r, f)
        self.y += 20

    def finish(self, note: str, seed: int, handwritten=False) -> bytes:
        self.y += 20
        self.text(f"নমুনা / SAMPLE · {note}", 20, color=MUTED)
        img = self.img.crop((0, 0, W, self.y + M))
        if handwritten:  # slanted ink: shear the page and tint the text blue
            sheared = img.transform(
                img.size,
                Image.Transform.AFFINE,
                (1, 0.12, -0.06 * img.height, 0, 1, 0),
                fillcolor="white",
            )
            r, g, b = sheared.split()
            img = Image.merge(
                "RGB",
                (
                    r.point(lambda v: min(255, v + 10)),
                    g.point(lambda v: min(255, v + 30)),
                    b.point(lambda v: max(v, 120)),
                ),
            )
        return _watermark(img, seed)


def _watermark(img: Image.Image, seed: int) -> bytes:
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    rng = random.Random(seed)
    for y in range(80, img.height, 300):
        for x in range(-100 + rng.randint(0, 60), img.width, 460):
            d.text((x, y), "নমুনা / SAMPLE", font=_font(46, True), fill=(170, 30, 30, 48))
    layer = layer.rotate(math.degrees(0.4), resample=Image.Resampling.BICUBIC)
    out = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")
    buf = BytesIO()
    out.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def _person(p: dict) -> str:
    marker = MARKER.get(p.get("relation_marker") or "", "পিতা")
    return f"{p['name']}\n{marker}- {p.get('father_or_husband_name') or ''}"


def _owners_and_plots(pg: Page, d: dict, owner_head: str):
    pg.table(
        ["ক্রমিক নং", owner_head, "অংশ"],
        [
            [bn(str(i + 1)), _person(o), o.get("share_text") or ""]
            for i, o in enumerate(d["owners"])
        ],
        [0.12, 0.66, 0.22],
    )
    unit = d.get("area_unit_text") or "একর"
    pg.table(
        [
            "দাগ নং",
            "জমির শ্রেণী",
            f"দাগের মোট জমি\n({unit})",
            "দাগের মধ্যে\nঅত্র খতিয়ানের অংশ",
            f"অংশানুযায়ী\nজমির পরিমাণ ({unit})",
        ],
        [
            [
                bn(p["dag_no"]),
                p.get("land_class") or "",
                p.get("plot_total_area_text") or "",
                p.get("khatian_share_text") or "",
                p.get("area_text") or "",
            ]
            for p in d["plots"]
        ]
        + [["", "", "", "মোট জমি", d.get("total_area_text") or ""]],
        [0.14, 0.16, 0.22, 0.24, 0.24],
    )


def render(f: SampleFile, seed: int) -> bytes:
    d, pg = f.data, Page()
    loc = d.get("location") or d.get("schedule_location") or {}
    if d["doc_type"] == "khatian":
        pg.text(f"{SURVEY.get(d.get('survey_type'), '')} খতিয়ান", 36, True, center=True)
        pg.text(f"খতিয়ান নং: {bn(d['khatian_no'])}", 26, True, center=True, gap=20)
        pg.pairs(
            [
                ("জেলা", loc.get("district", "")),
                ("থানা/উপজেলা", loc.get("upazila", "")),
                ("মৌজা", loc.get("mouza", "")),
                ("জে.এল. নং", bn(loc.get("jl_no") or "")),
            ]
        )
        _owners_and_plots(pg, d, "মালিক, অংশীদারের নাম ও ঠিকানা")
        return pg.finish("কৃত্রিম তথ্য, বাস্তব রেকর্ড নয়", seed)
    if d["doc_type"] == "deed":
        pg.text(DEED_LABEL.get(d.get("deed_type") or "other", "দলিল"), 36, True, center=True)
        if d.get("is_draft"):
            pg.text("(খসড়া)", 24, center=True)
        pg.pairs(
            [
                ("দলিল নং", bn(d.get("deed_no") or "") or "—"),
                ("সন", bn(d.get("deed_year") or "") or "—"),
                ("সাব-রেজিস্ট্রি অফিস", d.get("sub_registry_office") or ""),
                ("রেজিস্ট্রির তারিখ", d.get("registration_date_text") or "—"),
            ]
            + ([("বহি নং", bn(d["book_no"]))] if d.get("book_no") else [])
        )
        pg.text("দাতা / বিক্রেতা", 27, True)
        for s in d["sellers"]:
            pg.para(
                f"{s['name']}, {MARKER.get(s.get('relation_marker') or '', 'পিতা')}- {s.get('father_or_husband_name') or ''}, {s.get('address_text') or ''}"
            )
        pg.text("গ্রহীতা / ক্রেতা", 27, True)
        for b in d["buyers"]:
            pg.para(
                f"{b['name']}, {MARKER.get(b.get('relation_marker') or '', 'পিতা')}- {b.get('father_or_husband_name') or ''}, {b.get('address_text') or ''}"
            )
        if d.get("title_source_text"):
            pg.text("মালিকানার বিবরণ", 27, True)
            prior = [
                f"{bn(p.get('deed_no', ''))}/{bn(p.get('deed_year', ''))}"
                for p in d.get("prior_deeds") or []
            ]
            pg.para(
                f"নিম্ন তফসিল বর্ণিত সম্পত্তি দাতা {d['title_source_text']} হইয়া এ যাবৎ ভোগদখলকার আছেন"
                + (f" (বায়া দলিল নং {', '.join(prior)})" if prior else "")
                + "।"
            )
        pg.text("তফসিল", 27, True)
        khatians = ", ".join(
            f"{SURVEY.get(k.get('survey_type'), '')} {bn(k['khatian_no'])}"
            for k in d.get("schedule_khatians") or []
        )
        dags = ", ".join(
            f"{bn(p['dag_no'])} ({p.get('land_class') or ''})"
            for p in d.get("schedule_plots") or []
        )
        pg.table(
            ["বিবরণ", ""],
            [
                ["জেলা", loc.get("district", "")],
                ["উপজেলা / থানা", loc.get("upazila", "")],
                ["মৌজা", loc.get("mouza", "")],
                ["জে.এল. নং", bn(loc.get("jl_no") or "")],
                ["খতিয়ান নং", khatians],
                ["দাগ নং", dags],
                ["হস্তান্তরিত জমির পরিমাণ", d.get("transferred_area_text") or ""],
            ],
            [0.36, 0.64],
        )
        if d.get("price_text"):
            pg.text(f"পণ / মূল্য: {d['price_text']}", 23)
        return pg.finish("কৃত্রিম তথ্য, বাস্তব দলিল নয়", seed, handwritten=f.handwritten)
    if d["doc_type"] == "dcr":
        pg.text(d.get("office") or "", 22, center=True)
        pg.text("নামজারি খতিয়ান", 36, True, center=True)
        pg.text(
            f"নামজারি মোকদ্দমা নং: {bn(d.get('case_no') or '')}   আদেশের তারিখ: {d.get('order_date_text') or ''}",
            23,
            center=True,
            gap=18,
        )
        pg.pairs(
            [
                ("জেলা", loc.get("district", "")),
                ("উপজেলা", loc.get("upazila", "")),
                ("মৌজা", loc.get("mouza", "")),
                ("জে.এল. নং", bn(loc.get("jl_no") or "")),
                ("খতিয়ান নং", bn(d.get("new_khatian_no") or "")),
                ("পূর্বের খতিয়ান (এস.এ.)", bn(d.get("old_khatian_no") or "")),
                ("নামজারির কারণ", d.get("basis_text") or ""),
            ]
        )
        _owners_and_plots(pg, d, "মালিকের নাম ও ঠিকানা")
        if d.get("dcr_no"):
            pg.text(f"ডি.সি.আর. নং: {bn(d['dcr_no'])}   তারিখ: {d.get('dcr_date_text') or ''}", 23)
        return pg.finish("কৃত্রিম তথ্য, বাস্তব রেকর্ড নয়", seed)
    # heir certificate
    addr = d.get("deceased_address") or {}
    pg.text(d.get("issuing_authority") or "", 28, True, center=True)
    pg.text(
        f"উপজেলা- {addr.get('upazila', '')}, জেলা- {addr.get('district', '')}",
        22,
        center=True,
        gap=24,
    )
    pg.text("ওয়ারিশ সনদপত্র", 36, True, center=True, gap=18)
    pg.para(
        f"এই মর্মে প্রত্যয়ন করা যাইতেছে যে, মরহুম {d['deceased_name']}, পিতা- {d.get('deceased_father_or_husband_name') or ''}, "
        f"{addr.get('address_text', '')}, উপজেলা- {addr.get('upazila', '')}, জেলা- {addr.get('district', '')}, গত "
        f"{d.get('date_of_death_text') or ''} তারিখে মৃত্যুবরণ করেন। মৃত্যুকালে তিনি নিম্নলিখিত ওয়ারিশগণ রাখিয়া যান:"
    )
    pg.table(
        ["ক্রমিক নং", "ওয়ারিশের নাম", "সম্পর্ক"],
        [
            [bn(str(i + 1)), h["name"], h.get("relation_text") or ""]
            for i, h in enumerate(d["heirs"])
        ],
        [0.16, 0.6, 0.24],
    )
    pg.text(f"{d.get('issuer_title') or ''}, {d.get('issuing_authority') or ''}", 23)
    return pg.finish("কৃত্রিম তথ্য, বাস্তব সনদ নয়", seed)


def seed_for(land_id: uuid.UUID, name: str) -> int:
    return uuid.uuid5(land_id, name).int % 2**31
