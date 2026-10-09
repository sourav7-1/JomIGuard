import csv
from collections import defaultdict

import cv2
import numpy as np
import pytest

from synth.augment import PRESETS, augment_image, generate

PER_SOURCE = 3


def fake_page(text: str) -> np.ndarray:
    page = np.full((420, 320, 3), 255, np.uint8)
    for i in range(8):
        y = 40 + 45 * i
        cv2.putText(page, f"{text} line {i}", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, 0, 1)
    cv2.rectangle(page, (10, 10), (310, 410), 0, 1)
    return page


@pytest.fixture(scope="module")
def src(tmp_path_factory):
    root = tmp_path_factory.mktemp("src")
    docs = [
        root / "khatian" / "khatian_00001",
        root / "cases" / "case_00001" / "khatian",
        root / "cases" / "case_00001" / "deed",
    ]
    for d in docs:
        d.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(d.with_suffix(".png")), fake_page(d.name))
        d.with_suffix(".json").write_text('{"khatian_no": "882/1", "x": "৮৮২"}\n', encoding="utf-8")
    return root


@pytest.fixture(scope="module")
def out(src, tmp_path_factory):
    d = tmp_path_factory.mktemp("aug")
    generate(src, d, PER_SOURCE, seed=44)
    return d


def manifest(out):
    with (out / "manifest.csv").open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_same_seed_gives_byte_identical_images(src, out, tmp_path):
    generate(src, tmp_path, PER_SOURCE, seed=44)
    for row in manifest(out):
        assert (out / row["output"]).read_bytes() == (tmp_path / row["output"]).read_bytes()


def test_json_copied_unchanged(src, out):
    for row in manifest(out):
        copied = (out / row["output"]).with_suffix(".json").read_bytes()
        assert copied == (src / row["source"]).with_suffix(".json").read_bytes()


def test_copies_of_one_source_share_split(out):
    splits = defaultdict(set)
    for row in manifest(out):
        splits[row["source_id"]].add(row["split"])
    assert all(len(s) == 1 for s in splits.values())
    assert set().union(*splits.values()) <= {"train", "test"}


@pytest.mark.parametrize("preset", list(PRESETS))
def test_every_preset_produces_a_real_image(preset):
    img, params = augment_image(cv2.cvtColor(fake_page("x"), cv2.COLOR_BGR2RGB), preset, seed=1)
    assert img.ndim == 3 and img.shape[0] > 100 and img.shape[1] > 100
    assert img.std() > 5  # not empty, not all one colour
    assert 40 <= params["jpeg_quality"] <= 85


@pytest.mark.parametrize("preset", list(PRESETS))
def test_no_channel_blows_out(preset):
    # regression: A.RGBShift read a 1-pixel shift as "100%" and turned pages neon
    page = cv2.cvtColor(fake_page("x"), cv2.COLOR_BGR2RGB)
    for seed in range(10):
        img, _ = augment_image(page, preset, seed)
        means = img.reshape(-1, 3).mean(axis=0)
        # neon pages spread ~200; heavy warm cast (+-25) on a brown desk stays well under 100
        assert means.max() - means.min() < 100, (seed, means)


def test_manifest_has_one_row_per_output(out):
    rows = manifest(out)
    pngs = {p.name for p in out.glob("*.png")} - {"contact_sheet.png"}
    assert len(rows) == 3 * PER_SOURCE
    assert sorted(r["output"] for r in rows) == sorted(pngs)
    assert (out / "contact_sheet.png").exists()
