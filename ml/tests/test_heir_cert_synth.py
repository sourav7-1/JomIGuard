import pytest
from app.schemas.extracted import HeirCertData

from synth.deed import TITLES, generate_cases

N = 40


@pytest.fixture(scope="module")
def cases():
    return generate_cases(N, seed=9)


def test_about_half_are_family_cases(cases):
    family = [c for c in cases if c.family]
    assert 0.25 * N <= len(family) <= 0.75 * N
    for c in cases:
        assert (c.heir_cert is not None) == c.family
        assert ("heir_cert" in c.documents) == c.family
        assert c.deed.title_source_text == TITLES["inheritance" if c.family else "purchase"]


def test_heir_cert_json_validates_and_is_deterministic(cases):
    family = [c for c in cases if c.family]
    for c in family:
        HeirCertData.model_validate_json(c.heir_cert_json())
    again = [c for c in generate_cases(N, seed=9) if c.family]
    assert [c.heir_cert_json() for c in family] == [c.heir_cert_json() for c in again]


def test_heirs_match_khatian_owners(cases):
    for c in (c for c in cases if c.family):
        cert, owners = c.heir_cert, c.khatian.owners
        assert {h.name_normalized for h in cert.heirs} == {o.name_normalized for o in owners}
        # deceased is the owners' father (or husband, for the widow)
        assert {o.father_or_husband_name for o in owners} == {cert.deceased_name}
        assert all(h.father_or_husband_name == cert.deceased_name for h in cert.heirs)
        for h, o in zip(cert.heirs, owners, strict=True):
            expected = {"husband": {"wife"}, "father": {"son", "daughter"}}[o.relation_marker]
            assert h.relation in expected
        assert cert.date_of_death < cert.issue_date < c.mutation.order_date


def test_some_family_cases_include_the_widow(cases):
    relations = {h.relation for c in cases if c.family for h in c.heir_cert.heirs}
    assert {"son", "daughter", "wife"} <= relations
