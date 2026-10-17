import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest
from conftest import TestSession
from markupsafe import escape
from scenario_loader import load_scenario

from app.models import DocStatus, DocType, Document, Extraction, ExtractionStatus
from app.services.actions import next_actions
from app.services.ocr import ocr
from app.services.report import render_report_html, render_report_pdf
from app.services.risk import assess, forbidden_words_in
from app.services.rules import run_rules

SCENARIOS = Path(__file__).parents[1] / "scenarios"
ALL = sorted(p for p in SCENARIOS.iterdir() if p.is_dir())
WHEN = datetime(2026, 10, 15, 9, 30, tzinfo=UTC)


def report_for(folder: Path):
    case, _ = load_scenario(folder)
    run = run_rules(case)
    assessment = assess(case, run)
    assessment.actions = next_actions(case, run, assessment)
    return case, assessment, render_report_html(case, assessment, WHEN)


@pytest.fixture(scope="module")
def demo():
    return report_for(SCENARIOS / "01_demo_area_exceeds")


@pytest.fixture(scope="module")
def demo_pdf(demo):
    return render_report_pdf(demo[2])


def test_html_has_headline_findings_actions_and_disclaimer(demo):
    _, a, html = demo
    for text in [a.headline_bn, a.summary_bn, a.disclaimer_bn,
                 *(f.message_bn for f in a.findings), *(x.text_bn for x in a.actions),
                 *(p.message_bn for p in a.passed)]:  # fmt: skip
        assert str(escape(text)) in html, text  # autoescaped: " -> &#34;
    assert "এটি আইনি পরামর্শ নয়" in html and "আংশিক যাচাই" in html
    assert "১৫/১০/২০২৬" in html  # date in Bangla digits
    assert "নমুনা" in html  # scenario data: watermark
    # labelled printed values: the document is named once, then its values
    labelled = "খতিয়ানে রহিম উদ্দিনের অংশ .৪০০ · দাগ ৩০৫-এ জমি .১৫০০ একর · দলিলে দাগ ৩০৫-এ ১০ শতাংশ"
    assert "উৎস:" in html and labelled in html


def test_risk_level_colour_classes():
    _, _, high = report_for(SCENARIOS / "01_demo_area_exceeds")
    _, _, low = report_for(SCENARIOS / "02_sells_within_share")
    assert 'class="verdict risk-high"' in high and 'class="verdict risk-low"' in low


@pytest.mark.parametrize("folder", ALL, ids=lambda p: p.name)
def test_no_forbidden_words_in_any_report(folder):
    _, _, html = report_for(folder)
    assert forbidden_words_in(html) == []


def test_pdf_is_a_pdf_with_pages(demo_pdf):
    import pypdfium2 as pdfium

    assert demo_pdf.startswith(b"%PDF")
    assert len(pdfium.PdfDocument(demo_pdf)) >= 1


def test_bangla_is_shaped_correctly(demo_pdf):
    """Conjuncts only OCR back correctly if HarfBuzz shaped them in the PDF."""
    import pypdfium2 as pdfium

    page = pdfium.PdfDocument(demo_pdf)[0]
    image = page.render(scale=200 / 72).to_pil().convert("L")
    text = ocr(np.array(image), psm=3).text
    for word in ("উদ্দিন", "খতিয়ান", "অংশ", "শতাংশ"):
        assert word in text, word


def test_page_footer_uses_bangla_digits(demo_pdf):
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(demo_pdf)
    footer = pdf[0].get_textpage().get_text_range()
    total = len(pdf)
    digits = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
    assert f"পৃষ্ঠা ১ / {str(total).translate(digits)}" in footer.replace("\r\n", " ")


def test_report_endpoint_returns_pdf(client):
    land_id = client.post("/lands", json={"mouza": "chandshi", "dag_no": "305"}).json()["id"]
    with TestSession() as db:
        demo = SCENARIOS / "01_demo_area_exceeds"
        for name, doc_type in [("khatian_bs.json", DocType.khatian), ("deed.json", DocType.deed)]:
            doc_id = uuid.uuid4()
            db.add(Document(id=doc_id, land_id=uuid.UUID(land_id), doc_type=doc_type,
                            status=DocStatus.done, file_key=f"{doc_id}/x.png",
                            original_filename="x.png"))  # fmt: skip
            db.flush()
            data = json.loads((demo / name).read_text(encoding="utf-8"))
            db.add(Extraction(document_id=doc_id, extractor="fake", status=ExtractionStatus.ok,
                              data=data, warnings=[], field_flags={}))  # fmt: skip
        db.commit()
    assessment = client.post(f"/lands/{land_id}/assess").json()
    r = client.get(f"/lands/{land_id}/assessments/{assessment['id']}/report.pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
    assert 'filename="jomiguard-report-chandshi-305.pdf"' in r.headers["content-disposition"]
    missing = client.get(f"/lands/{land_id}/assessments/{uuid.uuid4()}/report.pdf")
    assert missing.status_code == 404


def test_one_check_line_per_rule(demo):
    _, a, html = demo
    assert html.count('class="tick"') == len(a.passed) == 9
    assert "৩ জন ওয়ারিশই নামজারি (কেস ৫১২/১৮)-এ আছেন" in html
    assert "মালিকদের অংশ মিলিয়ে পুরো ১৫ শতাংশ — মোট জমির সমান" in html


def test_documents_table_area_and_khatian_with_survey(demo):
    _, _, html = demo
    assert "১৫ শতাংশ (.১৫০০ একর)" in html  # shatangsho first, printed form after
    assert html.count("<td>BS ৮৮২</td>") == 2  # khatian row and mutation row


def test_text_layer_is_copyable(demo_pdf):
    """ActualText spans + fixed ToUnicode: text extracted from the PDF is the real text."""
    import pypdfium2 as pdfium
    from rapidfuzz import fuzz

    from app.services.normalize import nfc

    pdf = pdfium.PdfDocument(demo_pdf)
    text = nfc(" ".join(pdf[i].get_textpage().get_text_range() for i in range(len(pdf))))
    assert "JomiGuard" in text and "৩০৫" in text
    for word in ("রহিম", "খতিয়ান", "শতাংশ", "রিপোর্ট", "বর্তমান"):
        assert fuzz.partial_ratio(nfc(word), text) >= 80, word
        assert nfc(word) in text, word  # with ActualText the words come out exactly
