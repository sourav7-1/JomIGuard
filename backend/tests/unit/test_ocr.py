import os
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytesseract
import pytest
from PIL import Image, ImageDraw, ImageFont

from app.services.ocr import OcrError, ocr, tesseract_version

FONT = Path(__file__).parents[1] / "fixtures/fonts/notosansbengali/NotoSansBengali.ttf"
TEXT = "দাগ নং ৩০৫ খতিয়ান ৮৮২"


@pytest.fixture(autouse=True)
def fresh_tesseract_check():
    tesseract_version.cache_clear()  # mocks below must not leak through the cache
    yield
    tesseract_version.cache_clear()


def render(text: str, size=(900, 140)) -> np.ndarray:
    # RAQM = HarfBuzz shaping: correct Bangla conjuncts and vowel-sign order
    font = ImageFont.truetype(str(FONT), 52, layout_engine=ImageFont.Layout.RAQM)
    img = Image.new("L", size, 255)
    ImageDraw.Draw(img).text((30, 35), text, font=font, fill=0)
    return np.array(img)


def test_reads_bangla_digits():
    res = ocr(render(TEXT))
    assert "৩০৫" in res.text and "৮৮২" in res.text, res.text
    assert res.lang == "ben+eng" and res.psm == 3 and res.tesseract_version


def test_default_model_is_tessdata_best():
    # set in backend/Dockerfile; tessdata_best ben is ~11 MB, the apt (fast) one ~1-2 MB
    folder = Path(os.environ["TESSDATA_PREFIX"])
    assert folder.name == "tessdata_best"
    assert (folder / "ben.traineddata").stat().st_size > 8_000_000
    assert {"ben", "eng"} <= set(pytesseract.get_languages(config=""))


def test_word_boxes_inside_image_and_confidences_in_range():
    img = render(TEXT)
    res = ocr(img)
    assert res.words
    h, w = img.shape
    for word in res.words:
        x, y, bw, bh = word.bbox
        assert 0 <= x and 0 <= y and x + bw <= w and y + bh <= h, word
        assert word.confidence is None or 0 <= word.confidence <= 100
    assert 0 <= res.mean_confidence <= 100
    assert {word.line for word in res.words} == {0}  # one rendered line


def test_blank_image_gives_empty_text():
    res = ocr(np.full((200, 400), 255, np.uint8))
    assert res.text == "" and res.words == [] and res.mean_confidence is None


def test_missing_language_pack_is_a_clear_error():
    with patch.object(pytesseract, "get_languages", return_value=["eng", "osd"]):
        with pytest.raises(OcrError, match="language pack missing: ben"):
            ocr(render(TEXT))


def test_missing_tesseract_is_a_clear_error():
    with patch.object(
        pytesseract, "get_tesseract_version", side_effect=pytesseract.TesseractNotFoundError()
    ):
        with pytest.raises(OcrError, match="not installed"):
            ocr(render(TEXT))


def test_rejects_non_image():
    with pytest.raises(OcrError, match="image array"):
        ocr(np.array([]))
