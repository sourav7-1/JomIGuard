"""Tesseract+regex baseline: parsing of handmade OCR text (shaped like real psm 3 output)."""

from datetime import date
from decimal import Decimal

import cv2
import numpy as np

from app.services.extraction import tesseract_regex as tr
from app.services.normalize import normalize_document

KHATIAN = """এস.এ. খতিয়ান
খতিয়ান নং: ১৩২৭
জেলা: রাজশাহী থান/উপজেলা: পবা মৌজা: দামকুড়া
জে.এল. নং: ১০৫ রেভিনিউ/তৌজি নং: ১৭৯০
we ae মালিক, অংশীদারের নাম ও ঠিকানা অংশ
১ মোঃ শফিক খান .৬০০
পিং- সেলিম সরকার
সাং- দামকুড়া
২ মোছাঃ রুনা বেগম ৪০০
জং- কামাল হোসেন
সাং- দামকুড়া
দাগনং জমির শ্রেণী দাগের মোট জমি (একর) দাগের মধ্যে অত্র খতিয়ানের অংশ অংশানুযায়ী জমির পরিমাণ (একর)
৮৮৬/৩ নাল ০৮৮০ ৫০০ ০৪৪০
৯০১ ভিটি .১০০০ ১.০০০ .১০০০
মোট জমি ১৪৪০
নমুনা / SAMPLE"""

MUTATION = """সহকারী কমিশনার (ভূমি) এর কার্যালয়, গোলাপগঞ্জ, সিলেট
নামজারি খতিয়ান
নামজারি মোকদ্দম| নং: ৭৯৪/৮৮ আদেশের তারিখ: ২৮/০২/১৯৮৮
মৌজা: ঢাকাদক্ষিণ
পূর্বের খতিয়ান (এস.এ.): ৮২১
জেলা: সিলেট
জে.এল. নং: ১০৩
হোল্টিং নং: ৬৮৩
উপজেলা: গোলাপগঞ্জ
খতিয়ান নং: ১৫০৫
নামজারির কারণ: ওয়ারিশ সূত্রে
ক্রমিক নং মালিকের নাম ও ঠিকানা অংশ
১ শেখ সিরাজুল উদ্দিন ২৫০
পিং-ইউসুফ মিয়া
সাং- ঢাকাদক্ষিণ
দাগনং জমির শ্রেণী দাগের মোট জমি (একর) দাগের মধ্যে অত্র খতিয়ানের অংশ অংশানুযায়ী জমির পরিমাণ (একর)
২৬৭৯ ডোবা ৩৮৩৬ ৫০০ ১৯১৮
মোট জমি ১৯১৮
ডুপ্লিকেট কার্বন রসিদ (ডি.সি.আর.)
ডি.সি.আ
নং: ৭১৮২৮৪
ফি: ৮৯০/- টাকা"""

DEED = """সাফ কবলা দলিল
দলিল নং: ৫৫৯১
সাব-রেজিস্ট্রি অফিস: গোলাপগঞ্জ
বহিনং: ১
সন: ২০১৪
রেতিস্ট্রির তারিখ: ০৮/১০/২০১৪
দাতা / বিক্রেতা
শেখ কামাল সরকার, পিতা- ইউসুফ মিয়া, সাং- ঢাকাদক্ষিণ, উপজেলা- গোলাপগঞ্জ, জেলা- সিলেট
গ্রহীতা / ক্রেতা
মোঃ মোস্তফা মিয়া, পিতা- জসিম আহমেদ, সাং- দামকুড়া, উপজেলা- পবা, জেলা- রাজশাহী
মালিকানার বিবরণ
নিম্ন তফসিল বর্ণিত সম্পত্তি দাতা ওয়ারিশ সূত্রে প্রাপ্ত হইয়া ভোগদখলকার আছেন (বায়া দলিল নং ১১৫৮৫/১৯৭৭, ৭০৯৭/২০১৩)।
তফসিল
জেলা সিলেট
উপজেলা / থানা গোলাপগঞ্জ
মৌজা ঢাকাদক্ষিণ
জে.এল. নং ১০৩
খতিয়ান নং আর.এস. ১৫০৫, এস.এ. ৭৫১
দাগ নং ২৬৭৯ (ডোবা)
হস্তানস্তরিত জমির পরিমাণ ১৮ শতাংশ
পণ / মূল্য: ৫৯,০৪,০০০/- টাকা
সাক্ষীগণ
১. মোঃ মিজানুর উদ্দিন, পিতা- হাবিবুর মোল্লা"""

HEIR = """গোলাপগঞ্জ পৌরসভা
উপজেলা- গোলাপগঞ্জ, জেলা- সিলেট
স্মারক নং: ৪৬৯/১৯৮৮ তারিখ: ০৩/০১/১৯৮৮
ওয়ারিশ সনদপত্র
এই মর্মে প্রত্যয়ন করা যাইতেছে যে, মরহুম ইউসুফ মিয়া, পিতা- রফিক হাওলাদার, গ্রাম- ঢাকাদক্ষিণ, উপজেলা- গোলাপগঞ্জ,
জেলা- সিলেট, গত ২৮/০১/১৯৮৭ তারিখে
মৃত্যুবরণ করেন। মৃত্যুকালে তিনি নিম্নলিখিত ওয়ারিশগণ রাখিয়া যান:
ব্রমিক নং ওয়ারিশের নাম সম্পর্ক
১ শেখ সিরাজুল উদ্দিন পুত্র
২ মোছাঃ জরিনা আক্তার কন্যা
© মোঃ জামাল আহমেদ a
আমার জানামতে উপরোক্ত ব্যক্তিগণ ব্যতীত মরহুমের অন্য কোনো ওয়ারিশ নাই।
মেয়র"""


def test_khatian_header_owners_and_plots():
    k = tr.parse(KHATIAN, "khatian")
    assert (k.survey_type, k.khatian_no, k.touzi_no) == ("SA", "1327", "1790")
    assert (k.location.district, k.location.upazila, k.location.mouza) == (
        "রাজশাহী",
        "পবা",
        "দামকুড়া",
    )
    assert k.location.jl_no == "105"
    assert [o.name for o in k.owners] == ["মোঃ শফিক খান", "মোছাঃ রুনা বেগম"]
    assert [o.share_text for o in k.owners] == [".৬০০", ".৪০০"]  # lost dot restored
    assert k.owners[1].relation_marker == "husband"
    assert k.owners[1].father_or_husband_name == "কামাল হোসেন"
    assert k.owners[0].address_text == "সাং- দামকুড়া"
    assert [p.dag_no for p in k.plots] == ["886/3", "901"]
    assert k.plots[0].area_text == ".০৪৪০" and k.plots[1].khatian_share_text == "১.০০০"
    assert k.area_unit_text == "একর" and k.total_area_text == ".১৪৪০"


def test_khatian_normalizes_to_shatangsho():
    k = normalize_document(tr.parse(KHATIAN, "khatian")).doc
    assert k.plots[0].area_shatangsho == Decimal("4.4")
    assert k.total_area_shatangsho == Decimal("14.4")
    assert k.owners[0].share_shatangsho == Decimal("0.6") * Decimal("14.4")


def test_mutation_fields_and_dcr_block():
    m = tr.parse(MUTATION, "dcr")
    assert (m.case_no, m.old_khatian_no, m.new_khatian_no) == ("794/88", "821", "1505")
    assert m.holding_no == "683" and m.dcr_no == "718284" and m.fee_taka == Decimal("890")
    assert m.order_date == date(1988, 2, 28) and m.order_date_text == "২৮/০২/১৯৮৮"
    assert m.office.startswith("সহকারী কমিশনার")
    assert m.basis_text == "ওয়ারিশ সূত্রে"
    assert m.location.upazila == "গোলাপগঞ্জ" and m.location.jl_no == "103"
    assert m.owners[0].share_text == ".২৫০" and m.plots[0].dag_no == "2679"


def test_deed_parties_schedule_and_price():
    d = tr.parse(DEED, "deed")
    assert d.deed_type == "saf_kabala" and d.is_draft is False
    assert (d.deed_no, d.deed_year, d.book_no) == ("5591", "2014", "1")
    assert d.registration_date == date(2014, 10, 8)  # label read as "রেতিস্ট্রির" still works
    assert d.sub_registry_office == "গোলাপগঞ্জ"
    assert d.sellers[0].name == "শেখ কামাল সরকার"
    assert d.sellers[0].father_or_husband_name == "ইউসুফ মিয়া"
    assert d.sellers[0].address_text.startswith("সাং- ঢাকাদক্ষিণ")
    assert d.buyers[0].name == "মোঃ মোস্তফা মিয়া"
    assert d.schedule_location.mouza == "ঢাকাদক্ষিণ" and d.schedule_location.jl_no == "103"
    assert [(r.survey_type, r.khatian_no) for r in d.schedule_khatians] == [
        ("RS", "1505"),
        ("SA", "751"),
    ]
    assert d.schedule_plots[0].dag_no == "2679" and d.schedule_plots[0].land_class == "ডোবা"
    assert d.transferred_area_text == "১৮ শতাংশ"
    assert d.price_taka == Decimal("5904000")
    prior = [(p.deed_no, p.deed_year) for p in d.prior_deeds]
    assert prior == [("11585", "1977"), ("7097", "2013")]
    assert d.title_source_text == "ওয়ারিশ সূত্রে প্রাপ্ত"


def test_draft_deed():
    d = tr.parse(DEED.replace("দলিল নং: ৫৫৯১\n", "(খসড়া)\n"), "deed")
    assert d.is_draft and d.deed_no is None


def test_heir_certificate():
    h = tr.parse(HEIR, "heir_cert")
    assert h.issuing_authority == "গোলাপগঞ্জ পৌরসভা" and h.issuer_title == "মেয়র"
    assert h.certificate_no == "469/1988" and h.issue_date == date(1988, 1, 3)
    assert h.deceased_name == "ইউসুফ মিয়া"
    assert h.deceased_father_or_husband_name == "রফিক হাওলাদার"
    assert h.deceased_address.address_text == "গ্রাম- ঢাকাদক্ষিণ"
    assert h.date_of_death == date(1987, 1, 28)
    assert [(x.name, x.relation) for x in h.heirs[:2]] == [
        ("শেখ সিরাজুল উদ্দিন", "son"),
        ("মোছাঃ জরিনা আক্তার", "daughter"),
    ]
    assert h.heirs[2].relation == "other"  # relation unreadable: not guessed


def test_garbage_text_still_gives_a_valid_document():
    for doc_type in ("khatian", "deed", "dcr", "heir_cert"):
        doc = tr.parse("কিছুই পড়া যায়নি", doc_type)
        assert doc.doc_type == doc_type


def test_extract_falls_back_to_psm6_and_costs_nothing(monkeypatch):
    calls = []

    def fake_ocr(image, psm):
        calls.append(psm)
        return type("R", (), {"text": "নমুনা" if psm == tr.PSM else KHATIAN})()

    monkeypatch.setattr(tr, "ocr", fake_ocr)
    png = cv2.imencode(".png", np.full((600, 500), 255, np.uint8))[1].tobytes()
    result = tr.TesseractRegexExtractor().extract(png, "khatian")
    assert calls == [tr.PSM, tr.FALLBACK_PSM]
    assert result.error is None and result.document.khatian_no == "1327"
    assert result.meta.cost_usd == 0 and result.meta.model == "tesseract_regex"


def test_extract_rejects_bad_input():
    ex = tr.TesseractRegexExtractor()
    assert ex.extract(b"not an image", "khatian").error.startswith("image")
    assert "unknown doc_type" in ex.extract(b"x", "letter").error
