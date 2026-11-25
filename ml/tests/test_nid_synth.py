"""Synthetic NID cards: fake placeholders, watermarked, ground truth = the three names only."""

import random

from synth.common import _TEMPLATES
from synth.nid import DOB, ID_NO, card, truth


def test_card_has_placeholders_and_the_truth_only_names():
    c = card(random.Random(1), 1)
    assert c["id_no"] == ID_NO and set(ID_NO) <= set("০ ") and DOB.endswith("1900")
    assert set(truth(c)) == {"name_bn", "name_en", "father_or_husband_name"}
    assert c["name_en"].startswith("SAMPLE")


def test_template_is_watermarked():
    html = _TEMPLATES.get_template("nid.html").render(font_faces=[], **card(random.Random(2), 2))
    assert html.count("নমুনা / SAMPLE") >= 2
