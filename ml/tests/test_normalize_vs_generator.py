"""The backend normalize must reproduce the generators' derived fields (ground truth)."""

import pytest
from app.schemas.extracted import ExtractedDocument
from app.services.normalize import normalize_document
from pydantic import TypeAdapter

from synth.deed import generate_cases

DERIVED = {
    "name_normalized",
    "share_fraction",
    "share_shatangsho",
    "plot_total_area_shatangsho",
    "khatian_share_fraction",
    "area_shatangsho",
    "total_area_shatangsho",
    "transferred_area_shatangsho",
}
documents = TypeAdapter(ExtractedDocument)


def strip_derived(node):
    if isinstance(node, dict):
        return {k: None if k in DERIVED else strip_derived(v) for k, v in node.items()}
    if isinstance(node, list):
        return [strip_derived(v) for v in node]
    return node


def case_documents():
    # family cases add heir certificates; every case has a khatian, a deed and a mutation
    for c in generate_cases(30, seed=11):
        docs = [c.khatian, c.deed, c.mutation] + ([c.heir_cert] if c.family else [])
        for doc in docs:
            yield pytest.param(doc, id=f"{c.id}-{doc.doc_type}")


@pytest.mark.parametrize("truth", list(case_documents()))
def test_normalize_matches_generator(truth):
    raw = documents.validate_python(strip_derived(truth.model_dump()))
    result = normalize_document(raw)
    assert result.doc == truth
    assert result.warnings == []


def test_all_document_types_covered():
    types = {p.values[0].doc_type for p in case_documents()}
    assert types == {"khatian", "deed", "dcr", "heir_cert"}
