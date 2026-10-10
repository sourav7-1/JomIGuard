import hashlib
import shutil

import pytest

from synth.dataset import build, data_files, run_commands, verify

SMALL = [
    {"module": "synth.khatian", "args": ["--n", "2", "--seed", "1"], "out": "synthetic/khatian"},
    {
        "module": "synth.deed",
        "args": ["--n", "2", "--seed", "2", "--mismatch-rate", "0.5"],
        "out": "synthetic/cases",
    },
    {
        "module": "synth.augment",
        "args": ["--per-source", "1", "--seed", "3"],
        "src": "synthetic",
        "out": "augmented",
    },
]


@pytest.fixture(scope="module")
def data(tmp_path_factory):
    root = tmp_path_factory.mktemp("data")
    run_commands(SMALL, root)
    return root


@pytest.fixture
def copy(data, tmp_path):
    """A private copy of the data that a test may tamper with."""
    return shutil.copytree(data, tmp_path / "data")


def test_build_lists_every_file_with_its_sha256(data, tmp_path):
    manifest = build("t", data, SMALL, tmp_path / "t.json")
    listed = {f["path"]: f for f in manifest["files"]}
    on_disk = data_files(SMALL, data)
    assert set(listed) == set(on_disk)
    for rel, p in on_disk.items():
        assert listed[rel]["sha256"] == hashlib.sha256(p.read_bytes()).hexdigest()
    deed = next(f for f in manifest["files"] if f["path"].endswith("deed.json"))
    assert deed["doc_type"] == "deed" and deed["split"] in ("train", "test")
    assert manifest["counts"]["cases"] == 2
    clean_pngs = [p for p in on_disk if p.startswith("synthetic/") and p.endswith(".png")]
    assert manifest["counts"]["augmented"] == len(clean_pngs)  # --per-source 1


def test_verify_passes_on_unchanged_data(data, tmp_path):
    build("t", data, SMALL, tmp_path / "t.json")
    report = verify(tmp_path / "t.json")
    assert report.ok, report
    assert report.checked == len(data_files(SMALL, data))


def test_verify_fails_when_a_json_is_edited(copy, tmp_path):
    edited = copy / "synthetic/cases/case_00001/deed.json"
    edited.write_text(edited.read_text(encoding="utf-8") + " ", encoding="utf-8")
    build("t", copy, SMALL, tmp_path / "t.json")
    report = verify(tmp_path / "t.json")
    assert not report.ok
    assert report.errors == ["synthetic/cases/case_00001/deed.json"]


def test_png_change_only_warns(copy, tmp_path):
    png = copy / "synthetic/khatian/khatian_00001.png"
    png.write_bytes(png.read_bytes() + b"\0")  # different bytes, same image
    build("t", copy, SMALL, tmp_path / "t.json")
    report = verify(tmp_path / "t.json")
    assert report.ok, report
    assert "synthetic/khatian/khatian_00001.png" in report.png_mismatches
