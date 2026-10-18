"""Bangla PDF report from an assessment (WeasyPrint). Pure: no DB, no network.

render_report_html(case, assessment, generated_at) -> HTML; render_report_pdf(html) -> PDF bytes.
Template, CSS and bundled OFL fonts live in app/report/. Numbers in Bangla digits; the text never
calls land safe (checked with risk.forbidden_words_in in the tests).
"""

import hashlib
import io
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.schemas.assessment import Assessment
from app.schemas.land_case import CaseDocument, LandCase, describe_sources
from app.services.normalize import to_bangla_digits
from app.services.rules.messages import show

REPORT_DIR = Path(__file__).resolve().parents[1] / "report"
_env = Environment(
    loader=FileSystemLoader(REPORT_DIR / "templates"), autoescape=select_autoescape(["html"])
)


def _bn(value) -> str:
    return to_bangla_digits(str(value))


def _is_sample(case: LandCase) -> bool:
    """Scenario or synthetic sample data: documents are named by file (e.g. "deed.json")."""
    return any(d.source_id.endswith(".json") for d in case.documents) or case.land_id is None


def _area_bn(doc: CaseDocument) -> str:
    """ "১৫ শতাংশ (.১৫০০ একর)": shatangsho first, the printed form after."""
    d = doc.data
    if doc.doc_type == "deed":
        shatangsho, printed = d.transferred_area_shatangsho, d.transferred_area_text
    else:
        shatangsho, printed = (
            getattr(d, "total_area_shatangsho", None),
            getattr(d, "total_area_text", None),
        )
        unit = getattr(d, "area_unit_text", None)
        if printed and unit and unit not in printed:
            printed = f"{printed} {unit}"
    if shatangsho is None:
        return _bn(printed or "")
    main = f"{show(shatangsho)} শতাংশ"
    return main if not printed or _bn(printed) == main else f"{main} ({_bn(printed)})"


def _doc_row(doc: CaseDocument, surveys: dict[str, str]) -> dict:
    d = doc.data
    people = (
        getattr(d, "owners", None) or getattr(d, "sellers", None) or getattr(d, "heirs", None) or []
    )
    names = ", ".join(p.name for p in people)
    plots = getattr(d, "plots", None) or getattr(d, "schedule_plots", None) or []
    if doc.doc_type == "khatian":
        khatian = f"{d.survey_type} {d.khatian_no}"
    elif doc.doc_type == "dcr":  # the mutation's khatian, with the survey of that khatian
        khatian = f"{surveys.get(d.new_khatian_no, '')} {d.new_khatian_no}".strip()
    elif doc.doc_type == "deed":
        khatian = ", ".join(f"{r.survey_type} {r.khatian_no}" for r in d.schedule_khatians)
    else:
        khatian = ""
    if doc.doc_type == "heir_cert":
        names = f"মৃত: {d.deceased_name}; ওয়ারিশ: {names}"
    return {
        "label": doc.label_bn,
        "handwritten": doc.doc_type == "deed" and doc.handwritten,
        "names": names,
        "dags": _bn(", ".join(p.dag_no for p in plots)),
        "khatian": _bn(khatian),
        "area": "" if doc.doc_type == "heir_cert" else _area_bn(doc),
    }


def render_report_html(
    case: LandCase, assessment: Assessment, generated_at: datetime, sample: bool | None = None
) -> str:
    current, deed = case.current_khatian, case.proposed_deed
    mouza = (current.data.location.mouza if current else None) or (
        deed.data.schedule_location.mouza if deed else None
    )
    dag_source = deed.data.schedule_plots if deed else (current.data.plots if current else [])
    dags = ", ".join(dict.fromkeys(p.dag_no for p in dag_source))
    surveys = {
        k.data.khatian_no: k.data.survey_type for k in case.documents_by_type.get("khatian", [])
    }
    key = f"{case.land_id or ''}|{generated_at.isoformat()}|{assessment.risk_level}"
    report_id = hashlib.sha256(key.encode()).hexdigest()[:8].upper()
    return _env.get_template("report.html").render(
        a=assessment,
        report_id=report_id,
        date_bn=_bn(generated_at.strftime("%d/%m/%Y")),
        mouza=mouza,
        dags=_bn(dags),
        khatian=current.label_bn if current else None,
        documents=[_doc_row(d, surveys) for d in case.documents],
        sample=_is_sample(case) if sample is None else sample,
        bn=_bn,
        describe_sources=describe_sources,
    )


# Bangla vowel signs drawn before the consonant: their glyph is separate, so a conjunct glyph's
# text must not repeat them
_PRE_BASE = "িেৈ"


def _fix_to_unicode(fonts) -> None:
    """Make the PDF text layer copyable (ToUnicode) for shaped Bangla.

    WeasyPrint maps each glyph id to the text of the first cluster it was drawn in, for the
    whole document: a pre-base vowel sign gets "" and the consonant after it gets "হি", which
    then reads as "হি" everywhere. Instead, every glyph that the font maps directly to a
    character gets that character; only conjunct/ligature glyphs keep their cluster text
    (without pre-base vowel signs, which have their own glyph). Copied text is then right
    except for pre-base vowel signs, which come out in visual order ("রিহম" for "রহিম").
    """
    from fontTools.ttLib import TTFont

    for font in fonts.values():
        if not font.to_unicode:
            continue
        try:
            ttfont = TTFont(io.BytesIO(font.file_content), lazy=True)
            cmap = ttfont.getBestCmap() or {}
        except Exception:  # noqa: BLE001  not a font fontTools can read: keep WeasyPrint's map
            continue
        direct: dict[int, str] = {}
        for codepoint, glyph_name in sorted(cmap.items()):
            direct.setdefault(ttfont.getGlyphID(glyph_name), chr(codepoint))
        for glyph_id, text in font.to_unicode.items():
            if glyph_id in direct:
                font.to_unicode[glyph_id] = direct[glyph_id]
            else:
                font.to_unicode[glyph_id] = "".join(c for c in text if c not in _PRE_BASE) or text


def _install_text_layer_fix() -> None:
    """Copyable Bangla text in the PDF (WeasyPrint 70).

    1. ActualText: every drawn line that is not plain ASCII is wrapped in
       /Span <</ActualText (line text)>> BDC … EMC, so extractors and viewers that honour
       ActualText get the logical text, whatever the glyph order.
    2. ToUnicode (_fix_to_unicode) for extractors that ignore ActualText.
    """
    # ponytail: wraps two WeasyPrint internals (draw.text.draw_first_line,
    # pdf.fonts.build_fonts_dictionary); test_report's text-layer test fails if an upgrade
    # changes them. Drop when WeasyPrint writes ActualText itself.
    import pydyf
    import weasyprint.draw.text as wtext
    import weasyprint.pdf as wpdf
    import weasyprint.pdf.fonts as wfonts

    if getattr(wtext.draw_first_line, "jomiguard_fix", False):
        return
    draw_line, build_fonts = wtext.draw_first_line, wfonts.build_fonts_dictionary

    def draw_first_line(stream, textbox, *args, **kwargs):
        text = textbox.text
        if not text.strip() or text.isascii():
            return draw_line(stream, textbox, *args, **kwargs)
        stream.begin_marked_content("Span", pydyf.Dictionary({"ActualText": pydyf.String(text)}))
        try:
            return draw_line(stream, textbox, *args, **kwargs)
        finally:
            stream.end_marked_content()

    def build_fonts_dictionary(pdf, fonts, *args, **kwargs):
        _fix_to_unicode(fonts)
        return build_fonts(pdf, fonts, *args, **kwargs)

    draw_first_line.jomiguard_fix = True
    wtext.draw_first_line = draw_first_line
    wfonts.build_fonts_dictionary = wpdf.build_fonts_dictionary = build_fonts_dictionary


def render_report_pdf(html: str) -> bytes:
    from weasyprint import HTML  # heavy import: only when a PDF is made

    _install_text_layer_fix()
    return HTML(string=html, base_url=str(REPORT_DIR)).write_pdf()
