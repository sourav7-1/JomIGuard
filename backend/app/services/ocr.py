"""Tesseract OCR (Bangla + English) on a preprocessed image.

ocr(image) -> OcrResult. Pass preprocess(...).gray: on augmented photos it found ~6x more
fields than .binary (data/preview/ocr/grid.md). The Bangla model is tessdata_best via
TESSDATA_PREFIX in backend/Dockerfile. No file I/O.
"""

from dataclasses import dataclass, field
from functools import cache

import cv2
import numpy as np
import pytesseract


class OcrError(RuntimeError):
    """Tesseract or a needed language pack is missing, or the input is not an image."""


@dataclass
class Word:
    text: str
    confidence: float | None  # 0-100; None where Tesseract reports -1
    bbox: tuple[int, int, int, int]  # x, y, width, height
    line: int  # 0-based line index in reading order


@dataclass
class OcrResult:
    text: str  # words joined by spaces, one line per OCR line
    words: list[Word] = field(default_factory=list)
    mean_confidence: float | None = None  # None when no word has a confidence
    lang: str = "ben+eng"
    psm: int = 3
    tesseract_version: str = ""


@cache
def tesseract_version(lang: str) -> str:
    """Tesseract version; raises OcrError if Tesseract or a language pack is missing."""
    try:
        version = str(pytesseract.get_tesseract_version())
        available = set(pytesseract.get_languages(config=""))
    except pytesseract.TesseractNotFoundError as e:
        raise OcrError("Tesseract is not installed or not on PATH") from e
    missing = [code for code in lang.split("+") if code not in available]
    if missing:
        raise OcrError(
            f"Tesseract language pack missing: {', '.join(missing)} "
            f"(installed: {', '.join(sorted(available))}); e.g. apt install tesseract-ocr-ben"
        )
    return version


def ocr(image: np.ndarray, lang: str = "ben+eng", psm: int = 3) -> OcrResult:
    if not isinstance(image, np.ndarray) or image.ndim not in (2, 3) or image.size == 0:
        raise OcrError("expected a non-empty 2D (gray) or 3D (BGR) image array")
    version = tesseract_version(lang)
    if image.ndim == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    data = pytesseract.image_to_data(
        image, lang=lang, config=f"--psm {psm}", output_type=pytesseract.Output.DICT
    )
    words, lines = [], {}
    for i, raw in enumerate(data["text"]):
        text = raw.strip()
        if not text:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        conf = float(data["conf"][i])
        words.append(
            Word(
                text=text,
                confidence=None if conf < 0 else conf,
                bbox=(data["left"][i], data["top"][i], data["width"][i], data["height"][i]),
                line=lines.setdefault(key, len(lines)),
            )
        )

    by_line: dict[int, list[str]] = {}
    for w in words:
        by_line.setdefault(w.line, []).append(w.text)
    confidences = [w.confidence for w in words if w.confidence is not None]
    return OcrResult(
        text="\n".join(" ".join(by_line[n]) for n in sorted(by_line)),
        words=words,
        mean_confidence=round(sum(confidences) / len(confidences), 2) if confidences else None,
        lang=lang,
        psm=psm,
        tesseract_version=version,
    )
