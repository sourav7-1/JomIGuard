import pytest
from app.schemas.extracted import MutationData

from synth.deed import generate_cases


@pytest.fixture(scope="module")
def cases():
    return generate_cases(40, seed=9)


def test_mutation_json_validates_and_is_deterministic(cases):
    for c in cases:
        MutationData.model_validate_json(c.mutation_json())
    again = generate_cases(40, seed=9)
    assert [c.mutation_json() for c in cases] == [c.mutation_json() for c in again]


def test_mutation_matches_case_khatian(cases):
    for c in cases:
        m, k = c.mutation, c.khatian
        assert m.new_khatian_no == k.khatian_no
        assert m.location == k.location
        assert m.owners == k.owners  # names, fathers and shares, including derived fields
        assert m.plots == k.plots
        assert m.total_area_shatangsho == k.total_area_shatangsho
        assert m.area_unit_text == "একর"
        assert m.case_no.split("/")[1] == f"{m.order_date.year % 100:02d}"
        assert m.order_date < m.dcr_date
        assert m.order_date.year < 2005  # before every deed (synth.deed uses 2005-2025)
        assert m.basis_text == ("ওয়ারিশ সূত্রে" if c.family else "ক্রয় সূত্রে")
