import struct

import cv2
import numpy as np
import pytest

from app.services.preprocess import PreprocessError, preprocess

BG = (70, 110, 150)  # BGR: a brown/blue desk colour
PAGE_W, PAGE_H = 600, 800


def text_page() -> np.ndarray:
    """White page with dark word-like blocks on evenly spaced lines."""
    rng = np.random.default_rng(0)
    page = np.full((PAGE_H, PAGE_W, 3), 255, np.uint8)
    for y in range(70, PAGE_H - 60, 36):
        x = 50
        while x < PAGE_W - 90:
            w = int(rng.integers(25, 80))
            cv2.rectangle(page, (x, y), (x + w, y + 12), (30, 30, 30), -1)
            x += w + int(rng.integers(10, 22))
    return page


def place(page: np.ndarray, quad, canvas=(1100, 1400)) -> np.ndarray:
    """Warp the page onto `quad` (tl, tr, br, bl) of a coloured canvas (w, h)."""
    h, w = page.shape[:2]
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    m = cv2.getPerspectiveTransform(src, np.float32(quad))
    out = np.full((canvas[1], canvas[0], 3), BG, np.uint8)
    warped = cv2.warpPerspective(page, m, canvas)
    mask = cv2.warpPerspective(np.full((h, w), 255, np.uint8), m, canvas) > 0
    out[mask] = warped[mask]
    return out


def rotated_quad(angle: float, canvas=(1100, 1400)):
    a = np.deg2rad(angle)
    rot = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    half = np.array([[-1, -1], [1, -1], [1, 1], [-1, 1]]) * [PAGE_W / 2, PAGE_H / 2]
    return half @ rot.T + np.array(canvas) / 2


def png(img: np.ndarray) -> bytes:
    return cv2.imencode(".png", img)[1].tobytes()


def residual_skew(binary: np.ndarray) -> float:
    """Median angle of the text lines in the output (independent of the service's estimator)."""
    ink = cv2.dilate(255 - binary, np.ones((3, 31), np.uint8))  # merge words into lines
    # RETR_LIST: the page border kept by the margin must not hide the lines inside it
    contours, _ = cv2.findContours(ink, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    angles = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if w > 200 and h < 60:  # a text line, not the page border
            vx, vy = cv2.fitLine(c, cv2.DIST_L2, 0, 0.01, 0.01).ravel()[:2]
            angles.append(np.degrees(np.arctan2(vy, vx)))
    assert len(angles) >= 5, "no text lines found in output"
    a = (np.array(angles) + 90) % 180 - 90  # fold to (-90, 90]
    return float(np.median(a))


@pytest.mark.parametrize("angle", [5, -8])
def test_rotated_page_is_straightened(angle):
    res = preprocess(png(place(text_page(), rotated_quad(angle))))
    assert abs(residual_skew(res.binary)) < 1.0, res.meta


def test_deskew_without_page_edge():
    # text fills the frame (no background, no page edge): only the deskew step can fix it
    page = cv2.warpAffine(
        text_page(),
        cv2.getRotationMatrix2D((PAGE_W / 2, PAGE_H / 2), 6, 1.0),
        (PAGE_W, PAGE_H),
        borderValue=(255, 255, 255),
    )
    res = preprocess(png(page))
    assert res.meta["page_found"] is False
    assert "deskew" in res.meta["steps"] and res.meta["deskew_angle"] == pytest.approx(-6, abs=1)
    assert abs(residual_skew(res.binary)) < 1.0


def test_perspective_page_found_and_aspect_kept():
    quad = [(180, 150), (850, 210), (900, 1250), (120, 1190)]
    res = preprocess(png(place(text_page(), quad)))
    assert res.meta["page_found"] is True
    w, h = res.meta["output_size"]
    assert w / h == pytest.approx(PAGE_W / PAGE_H, rel=0.06)


def test_inner_table_border_on_clean_scan_is_not_a_page():
    # flat scan, no background: the table border must not crop away the text around it
    page = text_page()
    cv2.rectangle(page, (30, 240), (570, 560), (0, 0, 0), 3)
    res = preprocess(png(page))
    assert res.meta["page_found"] is False, res.meta
    assert res.meta["output_size"] == [PAGE_W, PAGE_H]


def test_page_with_inner_table_on_background_is_found():
    page = text_page()
    cv2.rectangle(page, (30, 240), (570, 560), (0, 0, 0), 3)
    res = preprocess(png(place(page, rotated_quad(4))))
    assert res.meta["page_found"] is True
    w, h = res.meta["output_size"]
    assert w / h == pytest.approx(PAGE_W / PAGE_H, rel=0.06) and h > 0.9 * PAGE_H


def test_no_clear_page_warns_without_crashing():
    rng = np.random.default_rng(1)
    noise = cv2.GaussianBlur(rng.integers(0, 255, (900, 700, 3), dtype=np.uint8), (0, 0), 6)
    res = preprocess(png(noise))
    assert res.meta["page_found"] is False
    assert any("no page" in w for w in res.meta["warnings"])
    assert res.gray.size and res.binary.size


def test_large_image_is_resized_and_small_is_not_upscaled():
    large = preprocess(png(np.full((4000, 3000, 3), BG, np.uint8))).meta
    assert max(large["working_size"]) == 2000 and "resize" in large["steps"]
    assert large["original_size"] == [3000, 4000]
    small = preprocess(png(np.full((400, 500, 3), BG, np.uint8))).meta
    assert small["working_size"] == small["original_size"] == [500, 400]
    assert "resize" not in small["steps"]


def test_gray_and_binary_shapes_and_values():
    res = preprocess(png(place(text_page(), rotated_quad(3))))
    assert res.gray.shape == res.binary.shape and res.gray.ndim == 2
    assert set(np.unique(res.binary)) <= {0, 255}


@pytest.mark.parametrize("data", [b"", b"definitely not an image", b"\xff\xd8\xff\xe0garbage"])
def test_corrupt_bytes_raise_clear_error(data):
    with pytest.raises(PreprocessError, match="image"):
        preprocess(data)


def test_exif_orientation_is_respected():
    jpg = cv2.imencode(".jpg", np.full((200, 300, 3), 255, np.uint8))[1].tobytes()
    tiff = b"MM\x00\x2a" + struct.pack(">IH", 8, 1)
    tiff += struct.pack(">HHIHH", 0x0112, 3, 1, 6, 0) + struct.pack(">I", 0)  # Orientation = 6
    payload = b"Exif\x00\x00" + tiff
    rotated_jpg = jpg[:2] + b"\xff\xe1" + struct.pack(">H", len(payload) + 2) + payload + jpg[2:]
    meta = preprocess(rotated_jpg).meta
    assert meta["original_size"] == [200, 300]  # 90 degrees clockwise: width and height swap
    assert "exif_orientation:6" in meta["steps"]
