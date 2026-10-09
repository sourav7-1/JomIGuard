import json
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

from app.schemas.extracted import (
    DeedData,
    ExtractedDocument,
    HeirCertData,
    KhatianData,
    MutationData,
)

SAMPLES = Path(__file__).parent.parent / "fixtures" / "samples"
CASES = [
    ("khatian.json", KhatianData),
    ("deed.json", DeedData),
    ("mutation.json", MutationData),
    ("heir_cert.json", HeirCertData),
]
extracted = TypeAdapter(ExtractedDocument)


def load(name):
    return json.loads((SAMPLES / name).read_text(encoding="utf-8"))


def is_derived(key):
    return key == "name_normalized" or key.endswith(("_shatangsho", "_fraction"))


def strip(obj, drop=is_derived):
    """Drop matching keys at any depth."""
    if isinstance(obj, dict):
        return {k: strip(v, drop) for k, v in obj.items() if not drop(k)}
    if isinstance(obj, list):
        return [strip(v, drop) for v in obj]
    return obj


@pytest.mark.parametrize(("name", "model"), CASES)
def test_sample_validates_as_own_schema_and_union(name, model):
    data = load(name)
    assert isinstance(model.model_validate(data), model)
    assert isinstance(extracted.validate_python(data), model)


@pytest.mark.parametrize(("name", "model"), CASES)
def test_raw_extractor_output_without_derived_fields_validates(name, model):
    raw = strip(load(name))
    assert isinstance(extracted.validate_python(raw), model)


@pytest.mark.parametrize(("name", "model"), CASES)
def test_validates_without_name_normalized(name, model):
    data = load(name)
    raw = strip(data, lambda k: k == "name_normalized")
    assert raw != data  # every sample carries name_normalized
    assert isinstance(model.model_validate(raw), model)


def test_heir_cert_address_without_mouza():
    data = load("heir_cert.json")
    data["deceased_address"] = {"upazila": "গৌরনদী", "address_text": "গ্রাম চাঁদশী"}
    assert HeirCertData.model_validate(data).deceased_address.mouza is None


@pytest.mark.parametrize(("name", "model"), CASES)
def test_unknown_extra_field_rejected(name, model):
    with pytest.raises(ValidationError, match="extra_forbidden"):
        model.model_validate({**load(name), "nid": "x"})


def test_nested_extra_field_rejected():
    data = load("khatian.json")
    data["owners"][0]["phone"] = "x"
    with pytest.raises(ValidationError, match="extra_forbidden"):
        KhatianData.model_validate(data)


def test_int_dag_no_rejected():
    data = load("khatian.json")
    data["plots"][0]["dag_no"] = 305
    with pytest.raises(ValidationError, match="string_type"):
        KhatianData.model_validate(data)


def test_invalid_survey_type_rejected():
    data = load("khatian.json")
    data["survey_type"] = "XX"
    with pytest.raises(ValidationError, match="enum"):
        extracted.validate_python(data)


def test_decimals_are_decimal_not_float():
    owner = KhatianData.model_validate(load("khatian.json")).owners[0]
    assert owner.share_fraction == Decimal("0.400")
    assert isinstance(owner.share_shatangsho, Decimal)
