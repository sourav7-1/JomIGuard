"""With ground-truth extraction, the rules must find every labelled mismatch and raise no false
alarm: this proves the rules and the generator agree (extraction errors are tested separately)."""

import pytest
from app.services.extraction import ExtractionMeta, ExtractionResult

from eval.e2e_cases import LABEL_CODES, metrics, run_case
from synth.deed import generate_cases


class GroundTruthExtractor:
    def __init__(self, truth: dict[bytes, object]):
        self.truth = truth

    def extract(self, image_bytes: bytes, doc_type: str) -> ExtractionResult:
        doc = self.truth[image_bytes]
        stripped = doc.model_validate(doc.model_dump())  # a copy; normalize refills derived fields
        return ExtractionResult(document=stripped, meta=ExtractionMeta(model="ground-truth"))


@pytest.fixture(scope="module")
def results():
    out = []
    for c in generate_cases(60, seed=21):
        docs = [c.khatian, c.deed, c.mutation] + ([c.heir_cert] if c.family else [])
        names = ["khatian.json", "deed.json", "mutation.json", "heir_cert.json"]
        documents = [(n, f"{c.id}/{n}".encode(), d) for n, d in zip(names, docs, strict=False)]
        truth = {image: doc for _, image, doc in documents}
        expected = {m["type"] for m in c.mismatches} & LABEL_CODES
        out.append(
            run_case(
                c.id,
                c.family,
                expected,
                documents,
                GroundTruthExtractor(truth),
                classify=lambda image, t=truth: t[image].doc_type,
            )  # fmt: skip
        )
    return out


def test_every_labelled_mismatch_is_detected(results):
    m = metrics(results)
    assert m["expected"] > 0
    assert m["detected"] == m["expected"], [
        (r.case_id, r.expected, r.found) for r in results if r.missed
    ]


def test_no_false_alarms_and_no_extra_warnings(results):
    m = metrics(results)
    assert m["clean_cases"] > 0
    assert m["false_alarms"] == 0, [(r.case_id, r.extra_bad) for r in results if r.extra_bad]
    extras = [(r.case_id, r.expected, r.extra_bad, r.extra_warn) for r in results
              if r.extra_bad or r.extra_warn]  # fmt: skip
    assert extras == []


def test_ground_truth_has_no_causes_and_risk_follows_findings(results):
    for r in results:
        assert r.causes == [] and r.unread == []
        assert r.risk == ("high" if r.found_bad else "medium" if r.found_warn else "low")


def test_heir_consent_is_allowed_only_with_area_exceeds_in_family_cases(results):
    for r in results:
        if "heir_consent_missing" in r.found:
            assert r.family and "area_exceeds_share" in r.expected
