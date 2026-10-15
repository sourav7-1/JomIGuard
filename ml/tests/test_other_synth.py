import csv

import cv2
import pytest

from synth.other import KINDS, generate


@pytest.fixture(scope="module")
def rows(tmp_path_factory):
    out = tmp_path_factory.mktemp("other")
    return out, generate(4, seed=7, out=out)


def test_one_clean_and_one_augmented_image_per_page(rows):
    out, rs = rows
    assert len(rs) == 8
    assert {r["kind"] for r in rs} == set(KINDS)
    assert sum(r["preset"] == "clean" for r in rs) == 4
    assert {r["preset"] for r in rs if r["preset"] != "clean"} <= {"light", "medium", "heavy"}
    for r in rs:
        img = cv2.imread(str(out / r["output"]))
        assert img is not None and img.shape[0] > 500 and img.shape[1] > 500


def test_manifest_matches_and_is_deterministic(rows, tmp_path):
    out, rs = rows
    with (out / "manifest.csv").open(encoding="utf-8") as f:
        assert [r["output"] for r in csv.DictReader(f)] == [r["output"] for r in rs]
    again = generate(4, seed=7, out=tmp_path)
    assert again == rs
    assert (tmp_path / "manifest.csv").read_bytes() == (out / "manifest.csv").read_bytes()
