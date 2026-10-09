import csv
from decimal import Decimal

import pytest
from app.schemas.extracted import KhatianData

from synth.khatian import generate, generate_records, to_ascii, to_bn

N = 4


@pytest.fixture(scope="module")
def out(tmp_path_factory):
    d = tmp_path_factory.mktemp("khatian")
    generate(N, seed=7, out=d)
    return d


def ground_truths(out):
    return [
        KhatianData.model_validate_json(p.read_text(encoding="utf-8"))
        for p in sorted(out.glob("*.json"))
    ]


def test_ground_truth_validates(out):
    gts = ground_truths(out)
    assert len(gts) == N
    for k in gts:
        assert k.khatian_no.isascii() and k.location.jl_no.isascii()
        assert all(p.dag_no.isascii() for p in k.plots)
        # printed text uses Bangla digits only
        assert not any(c.isascii() and c.isdigit() for o in k.owners for c in o.share_text)
        assert all(not o.name_normalized.startswith(("মোঃ", "মোছাঃ", "শেখ")) for o in k.owners)
        # unit lives in the column header, never in the cell text
        assert k.area_unit_text == "একর"
        assert all("একর" not in p.area_text for p in k.plots)


def test_shares_and_areas_add_up(out):
    for k in ground_truths(out):
        assert sum(o.share_fraction for o in k.owners) == Decimal(1)
        assert sum(o.share_shatangsho for o in k.owners) == k.total_area_shatangsho
        assert sum(p.area_shatangsho for p in k.plots) == k.total_area_shatangsho


def test_same_seed_gives_identical_json():
    a = [r.ground_truth_json() for r in generate_records(20, seed=42)]
    b = [r.ground_truth_json() for r in generate_records(20, seed=42)]
    assert a == b
    assert a != [r.ground_truth_json() for r in generate_records(20, seed=43)]


def test_bangla_digit_conversion():
    assert to_bn("882/1") == "৮৮২/১"
    assert to_ascii("৮৮২/১") == "882/1"


def test_png_for_every_json(out):
    jsons = {p.stem for p in out.glob("*.json")}
    assert jsons == {p.stem for p in out.glob("*.png")}
    with (out / "manifest.csv").open(encoding="utf-8") as f:
        assert {row["id"] for row in csv.DictReader(f)} == jsons
