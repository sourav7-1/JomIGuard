import pytest

from app.services.classify import (
    ClassifyResult,
    check_user_label,
    classify_text,
)

KHATIAN = """বি.এস. খতিয়ান
খতিয়ান নং: ৮৮২ জেলা: বরিশাল থানা/উপজেলা: গৌরনদী মৌজা: চাঁদশী জে.এল. নং: ৪৫
রেভিনিউ/তৌজি নং: ১৫২০
ক্রমিক নং মালিক, অংশীদারের নাম ও ঠিকানা অংশ
১ মোঃ রহিম উদ্দিন পিং রহমান .৪০০
দাগ নং জমির শ্রেণী দাগের মোট জমি (একর) অংশানুযায়ী জমির পরিমাণ (একর)
৩০৫ নাল .১৫০০ ১.০০০ .১৫০০
বার্ষিক খাজনা: ২ টাকা"""

DEED = """সাফ কবলা দলিল
দলিল নং: ৪৫২১ সন: ২০১৮ সাব-রেজিস্ট্রি অফিস: গৌরনদী রেজিস্ট্রির তারিখ: ১২/০৬/২০১৮
দাতা / বিক্রেতা মোঃ রহিম উদ্দিন পিতা রহমান
গ্রহীতা / ক্রেতা রফিক আহমেদ
দাতা স্বেচ্ছায় উক্ত সম্পত্তি গ্রহীতার বরাবরে হস্তান্তর করিলেন
তফসিল জেলা বরিশাল মৌজা চাঁদশী খতিয়ান নং ৮৮২ দাগ নং ৩০৫
সাক্ষীগণ"""

MUTATION = """নামজারি খতিয়ান
নামজারি মোকদ্দমা নং: ৫১২/১৮ আদেশের তারিখ: ০১/০২/২০১৮
সহকারী কমিশনার (ভূমি) এর কার্যালয়, গৌরনদী, বরিশাল
জেলা: বরিশাল উপজেলা: গৌরনদী মৌজা: চাঁদশী জে.এল. নং: ৪৫ খতিয়ান নং: ৮৮২
পূর্বের খতিয়ান (এস.এ.): ২১৪ হোল্ডিং নং: ৩১২
ক্রমিক নং মালিকের নাম ও ঠিকানা অংশ
দাগ নং জমির শ্রেণী দাগের মোট জমি (একর) দাগের মধ্যে অত্র খতিয়ানের অংশ
ডুপ্লিকেট কার্বন রসিদ (ডি.সি.আর.) ডি.সি.আর. নং: ৭৭৮৮১২ ফি: ১,১৫০"""

HEIR = """৫ নং চাঁদশী ইউনিয়ন পরিষদ
ওয়ারিশ সনদপত্র
এই মর্মে প্রত্যয়ন করা যাইতেছে যে, মরহুম রহমান, পিতা- ইউসুফ আলী, গত ২০/০৮/২০০৯ তারিখে
মৃত্যুবরণ করেন। ক্রমিক নং ওয়ারিশের নাম সম্পর্ক
১ রহিম উদ্দিন পুত্র ২ সালমা খাতুন কন্যা
চেয়ারম্যান"""


@pytest.mark.parametrize(
    ("text", "expected"),
    [(KHATIAN, "khatian"), (DEED, "deed"), (MUTATION, "dcr"), (HEIR, "heir_cert")],
)
def test_each_type(text, expected):
    res = classify_text(text)
    assert res.doc_type == expected, res
    assert 0 < res.confidence <= 1
    assert res.matched_keywords[expected]
    assert res.scores[expected] == max(res.scores.values())


def test_mutation_with_khatian_words_is_dcr():
    res = classify_text(MUTATION)
    assert res.scores["khatian"] > 0  # the khatian table words are there...
    assert res.doc_type == "dcr"  # ...but the mutation's own words weigh more


def test_one_wrong_letter_in_keywords_still_works():
    # OCR slips: নামজারি -> নামজারী, মোকদ্দমা -> মোকদ্দমো, কার্বন রসিদ -> কার্বন রশিদ
    noisy = (
        MUTATION.replace("নামজারি", "নামজারী")
        .replace("মোকদ্দমা", "মোকদ্দমো")
        .replace("কার্বন রসিদ", "কার্বন রশিদ")
    )
    assert "নামজারি" not in noisy
    res = classify_text(noisy)
    assert res.doc_type == "dcr" and "নামজারি" in res.matched_keywords["dcr"]


def test_zero_width_characters_are_ignored():
    res = classify_text(HEIR.replace("ওয়ারিশ", "ওয়া‌রিশ"))
    assert res.doc_type == "heir_cert" and "ওয়ারিশ" in res.matched_keywords["heir_cert"]


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   \n ",
        "বাজারের তালিকা চাল ২ কেজি ডাল ১ কেজি সয়াবিন তেল ১ লিটার পেঁয়াজ ৩ কেজি",
        "Dear A. Rahman, thank you for your letter about the community garden project.",
        "12 4093 77812 3 991 20441 7 66 13 802",
    ],
)
def test_empty_and_unrelated_text_is_other(text):
    res = classify_text(text)
    assert res.doc_type == "other"


def test_two_types_too_close_is_other():
    # half a deed and half an heir certificate: neither clearly wins
    res = classify_text("দলিল দাতা গ্রহীতা তফসিল ওয়ারিশ সনদপত্র প্রত্যয়ন মরহুম")
    assert res.doc_type == "other" and res.confidence < 0.4


def test_check_user_label_warns_only_on_mismatch():
    deed = classify_text(DEED)
    assert check_user_label("deed", deed) is None
    warning = check_user_label("khatian", deed)
    assert warning.code == "doc_type_mismatch"
    assert "খতিয়ান" in warning.message_bn and "দলিল" in warning.message_bn
    unclear = check_user_label("deed", ClassifyResult("other", 0.0))
    assert unclear.code == "doc_type_unclear" and unclear.message_bn
    for w in (warning, unclear):
        assert "নিরাপদ" not in w.message_bn


def test_psm_fallback_only_when_psm3_is_other():
    from app.services.classify import FALLBACK_PSM, PSM, classify_ocr

    calls = []

    def reader(texts):
        def read(psm):
            calls.append(psm)
            return texts[psm]

        return read

    # psm 3 finds only the footer; sparse-text mode reads the khatian
    res = classify_ocr(reader({PSM: "নমুনা / SAMPLE", FALLBACK_PSM: KHATIAN}))
    assert res.doc_type == "khatian" and calls == [PSM, FALLBACK_PSM]
    calls.clear()
    assert classify_ocr(reader({PSM: DEED})).doc_type == "deed" and calls == [PSM]
    calls.clear()
    assert classify_ocr(reader({PSM: "", FALLBACK_PSM: "চাল ২ কেজি"})).doc_type == "other"
