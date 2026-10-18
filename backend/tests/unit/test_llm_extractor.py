"""AnthropicExtractor with a mocked client: no network, no API key."""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from app.core.config import settings
from app.schemas.extracted import KhatianData
from app.services.extraction import Budget, BudgetExceeded
from app.services.extraction.budget import cost_usd
from app.services.extraction.llm import AnthropicExtractor, extractor_schema, is_normalize_field
from app.services.extraction.prompts import TOOL_NAME

SAMPLE = Path(__file__).parents[1] / "fixtures/samples/khatian.json"
DERIVED = {"name_normalized", "share_fraction", "share_shatangsho", "plot_total_area_shatangsho",
           "khatian_share_fraction", "area_shatangsho", "total_area_shatangsho",
           "transferred_area_shatangsho"}  # fmt: skip


def without_derived(node):
    if isinstance(node, dict):
        return {k: without_derived(v) for k, v in node.items() if k not in DERIVED}
    if isinstance(node, list):
        return [without_derived(v) for v in node]
    return node


def extractor_output() -> dict:
    """What a good model answer looks like: printed fields only."""
    return without_derived(json.loads(SAMPLE.read_text(encoding="utf-8")))


class FakeClient:
    def __init__(self, tool_input: dict, stop_reason: str = "tool_use"):
        self.calls = []
        self.messages = SimpleNamespace(create=self.create)
        self.tool_input, self.stop_reason = tool_input, stop_reason

    def create(self, **kwargs):
        self.calls.append(kwargs)
        block = SimpleNamespace(type="tool_use", name=TOOL_NAME, input=self.tool_input)
        return SimpleNamespace(
            content=[block],
            stop_reason=self.stop_reason,
            usage=SimpleNamespace(input_tokens=3000, output_tokens=1000),
        )


@pytest.fixture
def image() -> bytes:
    page = np.full((900, 700), 255, np.uint8)
    for y in range(80, 800, 40):
        cv2.line(page, (60, y), (640, y), 0, 3)
    return cv2.imencode(".png", page)[1].tobytes()


def make(tmp_path, client, limit="10", **kw) -> AnthropicExtractor:
    return AnthropicExtractor(
        client=client,
        model="test-model",
        price_input_per_mtok=Decimal("1"),
        price_output_per_mtok=Decimal("5"),
        max_tokens=4000,
        cache_dir=tmp_path / "cache",
        budget=Budget(tmp_path / "spend.json", Decimal(limit), today=lambda: date(2026, 10, 15)),
        **kw,
    )


def all_keys(node) -> set[str]:
    if isinstance(node, dict):
        keys = (
            set(node.get("properties", {})) if isinstance(node.get("properties"), dict) else set()
        )
        return keys | {k for v in node.values() for k in all_keys(v)}
    if isinstance(node, list):
        return {k for v in node for k in all_keys(v)}
    return set()


@pytest.mark.parametrize("doc_type", ["khatian", "deed", "dcr", "heir_cert"])
def test_extractor_schema_has_no_normalize_fields(doc_type):
    keys = all_keys(extractor_schema(doc_type))
    assert not [k for k in keys if is_normalize_field(k)]
    assert DERIVED.isdisjoint(keys)
    assert {"nid", "phone", "birth_registration_no"}.isdisjoint(keys)
    assert "name" in keys and extractor_schema(doc_type)["type"] == "object"


def test_handwritten_metadata_is_separate_from_validated_document(tmp_path, image):
    output = {**extractor_output(), "handwritten": True}
    client = FakeClient(output)
    result = make(tmp_path, client).extract(image, "khatian")
    assert result.handwritten is True
    assert "handwritten" not in result.document.model_dump()
    schema = client.calls[0]["tools"][0]["input_schema"]
    assert schema["properties"]["handwritten"] == {"type": "boolean"}


def test_valid_output_comes_back_as_document(tmp_path, image):
    client = FakeClient(extractor_output())
    result = make(tmp_path, client).extract(image, "khatian")
    assert result.error is None and isinstance(result.document, KhatianData)
    assert result.document.khatian_no == "882"
    assert result.document.owners[0].share_fraction is None  # normalize fills it, not the LLM
    call = client.calls[0]
    assert call["model"] == "test-model"
    assert call["tool_choice"] == {"type": "tool", "name": TOOL_NAME}
    assert call["messages"][0]["content"][0]["source"]["media_type"] == "image/png"
    m = result.meta
    assert (m.input_tokens, m.output_tokens, m.cached) == (3000, 1000, False)
    assert m.cost_usd == pytest.approx(0.008)  # 3000 x 1 + 1000 x 5 per million
    assert m.prompt_version and m.model == "test-model"


def test_original_image_mode_sends_jpeg(tmp_path, image):
    client = FakeClient(extractor_output())
    make(tmp_path, client, image="original").extract(image, "khatian")
    assert client.calls[0]["messages"][0]["content"][0]["source"]["media_type"] == "image/jpeg"


@pytest.mark.parametrize(
    "bad",
    [
        {"doc_type": "khatian", "khatian_no": 882},  # wrong type, required fields missing
        {**extractor_output(), "owners": "রহিম"},
    ],
)
def test_invalid_output_is_an_error_not_an_exception(tmp_path, image, bad):
    result = make(tmp_path, FakeClient(bad)).extract(image, "khatian")
    assert result.document is None and result.error.startswith("invalid output")


def test_truncated_output_is_an_error(tmp_path, image):
    result = make(tmp_path, FakeClient(extractor_output(), "max_tokens")).extract(image, "khatian")
    assert result.document is None and "max_tokens" in result.error


def test_budget_guard_refuses_before_calling(tmp_path, image):
    client = FakeClient(extractor_output())
    extractor = make(tmp_path, client, limit="0.01")  # estimate: >= 4000 x 5 / 1e6 = 0.02
    with pytest.raises(BudgetExceeded):
        extractor.extract(image, "khatian")
    assert client.calls == []


def test_budget_tracks_todays_spend(tmp_path):
    day = [date(2026, 10, 15)]
    budget = Budget(tmp_path / "spend.json", Decimal("1"), today=lambda: day[0])
    budget.add(Decimal("0.6"))
    budget.add(Decimal("0.2"))
    assert budget.spent_today() == Decimal("0.8")
    with pytest.raises(BudgetExceeded):
        budget.check(Decimal("0.5"))
    day[0] = date(2026, 10, 16)
    budget.check(Decimal("0.5"))  # a new day starts at 0
    assert cost_usd(1_000_000, 0, Decimal("3"), Decimal("15")) == Decimal("3")


def test_second_identical_call_is_a_cache_hit(tmp_path, image):
    client = FakeClient(extractor_output())
    extractor = make(tmp_path, client)
    first = extractor.extract(image, "khatian")
    second = extractor.extract(image, "khatian")
    assert len(client.calls) == 1
    assert second.meta.cached and second.meta.cost_usd == 0
    assert second.document == first.document
    spent = json.loads((tmp_path / "spend.json").read_text(encoding="utf-8"))["spent_usd"]
    assert Decimal(spent) == Decimal("0.008")  # the hit added nothing
    make(tmp_path, client, image="original").extract(image, "khatian")
    assert len(client.calls) == 2  # image mode is part of the key


def test_nid_in_output_is_never_stored(tmp_path, image):
    nid = "1987654321098"
    out = extractor_output()
    out["owners"][0]["nid"] = nid
    result = make(tmp_path, FakeClient(out)).extract(image, "khatian")
    assert result.document is None and "nid" in result.error  # no field accepts it
    assert nid not in result.error


def test_missing_settings_refuse_to_start(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "llm_model", None)
    with pytest.raises(ValueError, match="LLM_MODEL"):
        AnthropicExtractor(
            model=None,
            price_input_per_mtok=Decimal("1"),
            price_output_per_mtok=Decimal("1"),
            budget=Budget(tmp_path / "s.json", Decimal("1")),
        )
