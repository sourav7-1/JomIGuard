import csv
import hashlib
import json

import pytest
from app.schemas.extracted import DeedData, KhatianData

from synth.deed import MISMATCH_TYPES, generate, generate_cases
from synth.khatian import generate_records

FILES = {"khatian.png", "khatian.json", "deed.png", "deed.json", "case.json"}


def broken_checks(k: KhatianData, d: DeedData) -> set[str]:
    """The cross-document checks a deed can fail; names match the mismatch types."""
    broken = set()
    owners = {o.name_normalized: o for o in k.owners}
    seller = owners.get(d.sellers[0].name_normalized)
    if seller is None:
        broken.add("seller_not_owner")
    elif d.transferred_area_shatangsho > seller.share_shatangsho:
        broken.add("area_exceeds_share")
    if d.schedule_plots[0].dag_no not in {p.dag_no for p in k.plots}:
        broken.add("dag_mismatch")
    if not any(
        r.survey_type == k.survey_type and r.khatian_no == k.khatian_no for r in d.schedule_khatians
    ):
        broken.add("khatian_mismatch")
    if d.schedule_location.mouza != k.location.mouza:
        broken.add("mouza_mismatch")
    return broken


@pytest.fixture(scope="module")
def out(tmp_path_factory):
    d = tmp_path_factory.mktemp("cases")
    generate(4, seed=11, mismatch_rate=0.5, out=d)
    return d


def test_rendered_cases_validate(out):
    case_dirs = sorted(p for p in out.iterdir() if p.is_dir())
    assert len(case_dirs) == 4
    for d in case_dirs:
        assert {p.name for p in d.iterdir()} == FILES
        KhatianData.model_validate_json((d / "khatian.json").read_text(encoding="utf-8"))
        DeedData.model_validate_json((d / "deed.json").read_text(encoding="utf-8"))
    with (out / "manifest.csv").open(encoding="utf-8") as f:
        assert [r["case_id"] for r in csv.DictReader(f)] == [d.name for d in case_dirs]


def test_clean_cases_are_consistent():
    for c in generate_cases(150, seed=1, mismatch_rate=0):
        assert c.mismatches == []
        assert broken_checks(c.khatian, c.deed) == set(), c.id
        if c.deed.is_draft:
            assert c.deed.deed_no is None and c.deed.registration_date is None


def test_each_mismatch_breaks_exactly_its_check():
    cases = generate_cases(150, seed=2, mismatch_rate=1)
    seen = set()
    for c in cases:
        (m,) = c.mismatches
        assert broken_checks(c.khatian, c.deed) == {m["type"]}, c.id
        assert m["khatian_value"] != m["deed_value"]
        seen.add(m["type"])
    assert seen == set(MISMATCH_TYPES)


def test_benign_name_variation():
    benign = [c for c in generate_cases(100, seed=3, mismatch_rate=0) if c.benign_name_variation]
    assert benign
    for c in benign:
        seller = c.deed.sellers[0]
        owner = next(o for o in c.khatian.owners if o.name_normalized == seller.name_normalized)
        assert seller.name != owner.name
        assert c.mismatches == [] and broken_checks(c.khatian, c.deed) == set()


def test_same_seed_identical_output():
    def dump(cases):
        return [(c.khatian_json(), c.deed_json(), c.case_json()) for c in cases]

    assert dump(generate_cases(30, seed=5)) == dump(generate_cases(30, seed=5))
    assert dump(generate_cases(30, seed=5)) != dump(generate_cases(30, seed=6))


def khatian_fingerprint(n: int, seed: int) -> str:
    h = hashlib.sha256()
    for r in generate_records(n, seed):
        row = [r.id, r.seed, r.font, r.ground_truth_json(), r.printed]
        h.update(json.dumps(row, ensure_ascii=False, sort_keys=True, default=str).encode())
    return h.hexdigest()


def test_khatian_output_unchanged_by_refactor():
    # recorded from synth/khatian.py before the common.py refactor
    assert khatian_fingerprint(5, 7) == (
        "11ae79f998b10dc897021e01974b74b2d65233df5ee1c8a602fc7a041219966e"
    )
    assert khatian_fingerprint(50, 42) == (
        "45256e77fb244320cd1f97b7437d48e6b8685e8caca4b536e7a2a2419e4f63f9"
    )
