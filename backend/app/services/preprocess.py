"""Straighten and clean phone photos of documents before OCR / vision.

preprocess(image_bytes) -> PreprocessResult(gray, binary, meta). Pure: no file I/O.
"""

import struct
from dataclasses import dataclass, field

import cv2
import numpy as np

MAX_SIDE = 2000  # long side after resize; never upscale
MIN_PAGE_SHARE = 0.2  # a page must cover at least this share of the image
PAGE_MARGIN = 0.01  # keep this much (of page size) around a detected page edge
MAX_SKEW = 15.0  # degrees
DETECT_SIDE = 800  # page detection and skew estimation run on a downscaled copy
EDGE_TOUCH = 0.02  # a page this close (share of long side) to all image edges fills the frame
BG_RING = 0.03  # ring width (share of short side) compared inside vs outside a page edge
BG_CONTRAST = 30  # gray levels between paper and background for a real page edge


class PreprocessError(ValueError):
    """The input could not be processed (e.g. not a decodable image)."""


@dataclass
class PreprocessResult:
    gray: np.ndarray  # cleaned grayscale: the input for Tesseract and the vision LLM
    binary: np.ndarray  # 0/255 black text on white; kept only for experiments
    meta: dict = field(default_factory=dict)


# --- 1. decode ---


def exif_orientation(data: bytes) -> int:
    """EXIF Orientation tag (1-8) from JPEG bytes; 1 if absent or unreadable."""
    if data[:2] != b"\xff\xd8":
        return 1
    i = 2
    while i + 4 <= len(data) and data[i] == 0xFF:
        marker = data[i + 1]
        size = struct.unpack(">H", data[i + 2 : i + 4])[0]
        if marker == 0xE1 and data[i + 4 : i + 10] == b"Exif\x00\x00":
            tiff = data[i + 10 : i + 2 + size]
            endian = {b"II": "<", b"MM": ">"}.get(tiff[:2])
            if endian is None or len(tiff) < 8:
                return 1
            ifd = struct.unpack(endian + "I", tiff[4:8])[0]
            if ifd + 2 > len(tiff):
                return 1
            (count,) = struct.unpack(endian + "H", tiff[ifd : ifd + 2])
            for k in range(count):
                entry = tiff[ifd + 2 + 12 * k : ifd + 14 + 12 * k]
                if len(entry) < 12:
                    break
                tag, _type, _n, value = struct.unpack(endian + "HHIH", entry[:10])
                if tag == 0x0112:
                    return value if 1 <= value <= 8 else 1
            return 1
        if marker == 0xDA:  # start of scan: no more metadata
            break
        i += 2 + size
    return 1


def apply_orientation(img: np.ndarray, orientation: int) -> np.ndarray:
    ops = {
        2: lambda m: cv2.flip(m, 1),
        3: lambda m: cv2.rotate(m, cv2.ROTATE_180),
        4: lambda m: cv2.flip(m, 0),
        5: lambda m: cv2.transpose(m),
        6: lambda m: cv2.rotate(m, cv2.ROTATE_90_CLOCKWISE),
        7: lambda m: cv2.flip(cv2.transpose(m), -1),
        8: lambda m: cv2.rotate(m, cv2.ROTATE_90_COUNTERCLOCKWISE),
    }
    return ops[orientation](img) if orientation in ops else img


def decode(image_bytes: bytes) -> tuple[np.ndarray, int]:
    if not isinstance(image_bytes, bytes | bytearray) or not image_bytes:
        raise PreprocessError("expected non-empty image bytes")
    buf = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(buf, cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION)
    if img is None:
        raise PreprocessError("could not decode image (corrupt or unsupported format)")
    orientation = exif_orientation(bytes(image_bytes[:65536]))
    return apply_orientation(img, orientation), orientation


def limit_size(img: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    scale = MAX_SIDE / max(h, w)
    if scale >= 1:
        return img
    return cv2.resize(img, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)


# --- 2. page detection ---


def order_corners(pts: np.ndarray) -> np.ndarray:
    """-> tl, tr, br, bl."""
    s, d = pts.sum(axis=1), np.diff(pts, axis=1).ravel()
    return np.array([pts[s.argmin()], pts[d.argmin()], pts[s.argmax()], pts[d.argmax()]])


def is_page_edge(small: np.ndarray, quad: np.ndarray) -> bool:
    """A real page edge nearly touches the image border or has a background around it.

    Otherwise the quad is something on the page (e.g. a table border on a clean scan), and
    cropping to it would drop the text outside it.
    """
    h, w = small.shape
    x, y, bw, bh = cv2.boundingRect(quad)
    m = EDGE_TOUCH * max(h, w)
    if x <= m and y <= m and x + bw >= w - m and y + bh >= h - m:
        return True
    k = odd(BG_RING * min(h, w))
    kernel = np.ones((k, k), np.uint8)
    mask = np.zeros_like(small)
    cv2.fillConvexPoly(mask, quad.astype(np.int32), 255)
    outside = (cv2.dilate(mask, kernel) > 0) & (mask == 0)
    inside = (mask > 0) & (cv2.erode(mask, kernel) == 0)
    if not outside.any() or not inside.any():
        return False
    # 90th percentile = paper/background level, ignoring ink and the edge line itself
    paper_in, paper_out = np.percentile(small[inside], 90), np.percentile(small[outside], 90)
    return abs(float(paper_in - paper_out)) >= BG_CONTRAST


def find_page(gray: np.ndarray) -> np.ndarray | None:
    """Largest convex 4-corner page edge covering a sensible share of the image, or None."""
    h, w = gray.shape
    scale = min(1.0, DETECT_SIDE / max(h, w))
    small = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (5, 5), 0)
    edges = cv2.Canny(small, 40, 120)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    area = small.shape[0] * small.shape[1]
    for c in sorted(contours, key=cv2.contourArea, reverse=True)[:10]:
        approx = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
        if (
            len(approx) == 4
            and cv2.isContourConvex(approx)
            and MIN_PAGE_SHARE * area <= cv2.contourArea(approx) <= 0.99 * area
            and is_page_edge(small, approx.reshape(4, 2))
        ):
            return order_corners(approx.reshape(4, 2).astype(np.float32) / scale)
    return None


def warp_page(img: np.ndarray, corners: np.ndarray) -> np.ndarray:
    """Perspective-warp the page to a rectangle, keeping a small margin around its edge."""
    center = corners.mean(axis=0)
    tl, tr, br, bl = corners
    w = max(np.linalg.norm(tr - tl), np.linalg.norm(br - bl))
    h = max(np.linalg.norm(bl - tl), np.linalg.norm(br - tr))
    grown = center + (corners - center) * (1 + 2 * PAGE_MARGIN)
    out_w, out_h = round(w * (1 + 2 * PAGE_MARGIN)), round(h * (1 + 2 * PAGE_MARGIN))
    dst = np.array([[0, 0], [out_w - 1, 0], [out_w - 1, out_h - 1], [0, out_h - 1]], np.float32)
    m = cv2.getPerspectiveTransform(grown.astype(np.float32), dst)
    return cv2.warpPerspective(img, m, (out_w, out_h), borderMode=cv2.BORDER_REPLICATE)


# --- 3. deskew ---


def rotate(img: np.ndarray, angle: float, fill) -> np.ndarray:
    """Rotate by `angle` degrees (counter-clockwise) on an enlarged canvas: nothing is cut off."""
    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    cos, sin = abs(m[0, 0]), abs(m[0, 1])
    nw, nh = int(h * sin + w * cos + 0.5), int(h * cos + w * sin + 0.5)
    m[0, 2] += nw / 2 - w / 2
    m[1, 2] += nh / 2 - h / 2
    return cv2.warpAffine(
        img, m, (nw, nh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=fill
    )


def estimate_skew(gray: np.ndarray) -> float | None:
    """Text angle in degrees (rotate by it to level the lines), or None if unreliable.

    Projection profile: the rotation that makes row ink sums most uneven aligns the text lines.
    """
    h, w = gray.shape
    scale = min(1.0, DETECT_SIDE / max(h, w))
    small = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    ink = cv2.threshold(small, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    ink_share = np.count_nonzero(ink) / ink.size
    if not 0.002 < ink_share < 0.4:
        return None

    def score(angle: float) -> float:
        rows = rotate(ink, angle, 0).sum(axis=1, dtype=np.float64)
        return float(np.var(rows))

    coarse = np.arange(-MAX_SKEW, MAX_SKEW + 0.5, 1.0)
    scores = np.array([score(a) for a in coarse])
    best = float(coarse[scores.argmax()])
    if abs(best) >= MAX_SKEW or scores.max() < 1.3 * np.median(scores):
        return None  # peak at the search edge or no clear peak: no reliable text lines
    fine = np.arange(best - 1.0, best + 1.01, 0.1)
    return round(float(fine[np.argmax([score(a) for a in fine])]), 2)


# --- 4-5. illumination and binarization ---


def odd(n: float) -> int:
    n = max(3, int(n))
    return n if n % 2 else n + 1


def flatten_illumination(gray: np.ndarray) -> np.ndarray:
    """Divide by a smoothed background: removes shadows and uneven light."""
    k = odd(min(gray.shape) / 25)
    background = cv2.morphologyEx(
        gray, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    )
    background = cv2.medianBlur(background, odd(k / 2) if k < 255 else 255)
    return cv2.divide(gray, np.maximum(background, 1), scale=255)


def binarize(flat: np.ndarray) -> np.ndarray:
    """Adaptive threshold of the shadow-corrected image *before* CLAHE.

    CLAHE amplifies sensor/JPEG noise on blank paper; thresholding after it left ~6000 specks
    per augmented page versus ~40 this way (median 3 removes the rest).
    """
    # the window must be wider than the thickest strokes, or bold text comes out hollow
    block = odd(min(flat.shape) / 12)
    return cv2.adaptiveThreshold(
        cv2.medianBlur(flat, 3), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block, 15
    )


# --- pipeline ---


def preprocess(image_bytes: bytes) -> PreprocessResult:
    img, orientation = decode(image_bytes)
    h, w = img.shape[:2]
    meta = {
        "original_size": [w, h],
        "page_found": False,
        "corners": None,
        "deskew_angle": 0.0,
        "steps": ["decode"],
        "warnings": [],
    }
    if orientation != 1:
        meta["steps"].append(f"exif_orientation:{orientation}")

    img = limit_size(img)
    if img.shape[:2] != (h, w):
        meta["steps"].append("resize")
    meta["working_size"] = [img.shape[1], img.shape[0]]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    corners = find_page(gray)
    if corners is not None:
        gray = warp_page(gray, corners)
        meta.update(page_found=True, corners=corners.round().astype(int).tolist())
        meta["steps"].append("page_warp")
    else:
        meta["warnings"].append("no page edge found; using the full image")

    angle = estimate_skew(gray)
    if angle is None:
        meta["warnings"].append("text angle unreliable; deskew skipped")
    elif abs(angle) >= 0.1:
        gray = rotate(gray, angle, 255)
        meta["deskew_angle"] = angle
        meta["steps"].append("deskew")

    flat = flatten_illumination(gray)
    gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(flat)
    meta["steps"] += ["illumination", "clahe"]
    binary = binarize(flat)
    meta["steps"].append("binarize")
    meta["output_size"] = [gray.shape[1], gray.shape[0]]
    return PreprocessResult(gray=gray, binary=binary, meta=meta)
