"""GeminiExtractor and the response-schema converter, with a mocked client (no network)."""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from google.genai import errors, types

from app.core.config import settings
from app.schemas.extracted import KhatianData
from app.services.extraction import Budget
from app.services.extraction import gemini as gm
from app.services.extraction.llm import AnthropicExtractor, make_llm_extractor

SAMPLE = Path(__file__).parents[1] / "fixtures/samples/khatian.json"
DERIVED = {"name_normalized", "share_fraction", "share_shatangsho", "plot_total_area_shatangsho",
           "khatian_share_fraction", "area_shatangsho", "total_area_shatangsho"}  # fmt: skip
FORBIDDEN_KEYS = {"$ref", "$defs", "anyOf", "const", "title", "default", "format", "pattern",
                  "additionalProperties"}  # fmt: skip


def printed_only(node):
    if isinstance(node, dict):
        return {k: printed_only(v) for k, v in node.items() if k not in DERIVED}
    if isinstance(node, list):
        return [printed_only(v) for v in node]
    return node


def answer() -> dict:
    return printed_only(json.loads(SAMPLE.read_text(encoding="utf-8")))


def all_keys(node) -> set[str]:
    if isinstance(node, dict):
        return set(node) | {k for v in node.values() for k in all_keys(v)}
    if isinstance(node, list):
        return {k for v in node for k in all_keys(v)}
    return set()


# --- schema converter ---


@pytest.mark.parametrize("doc_type", ["khatian", "deed", "dcr", "heir_cert"])
def test_converted_schema_is_inlined_and_accepted_by_the_sdk(doc_type):
    schema = gm.gemini_schema(doc_type)
    assert not (all_keys(schema) & FORBIDDEN_KEYS)
    assert schema["type"] == "object" and schema["properties"]["doc_type"]["enum"] == [doc_type]
    types.Schema.model_validate(schema)  # the SDK's own schema model accepts it


def test_converter_details():
    schema = gm.gemini_schema("deed")
    seller = schema["properties"]["sellers"]["items"]  # $ref inlined
    assert seller["type"] == "object" and "name" in seller["properties"]
    assert "name_normalized" not in seller["properties"]  # extractor-only schema
    assert seller["properties"]["father_or_husband_name"] == {"type": "string", "nullable": True}
    assert schema["properties"]["price_taka"] == {"type": "string", "nullable": True}  # Decimal
    assert schema["properties"]["registration_date"] == {"type": "string", "nullable": True}
    marker = seller["properties"]["relation_marker"]
    assert marker["enum"] == ["father", "husband", "unknown"] and marker["nullable"] is True
    assert "sellers" in schema["required"] and "price_taka" not in schema["required"]
    assert schema["properties"]["handwritten"] == {"type": "boolean"}
    assert "handwritten" in schema["required"]


def test_converter_on_a_small_handmade_schema():
    pydantic_like = {
        "$defs": {"P": {"properties": {"n": {"title": "N", "type": "string"}}, "required": ["n"],
                        "title": "P", "type": "object", "additionalProperties": False}},
        "properties": {"p": {"anyOf": [{"$ref": "#/$defs/P"}, {"type": "null"}], "default": None},
                       "k": {"const": "x", "type": "string"},
                       "ps": {"items": {"$ref": "#/$defs/P"}, "type": "array"}},
        "required": ["k"], "title": "Root", "type": "object",
    }  # fmt: skip
    assert gm.to_gemini_schema(pydantic_like) == {
        "type": "object",
        "required": ["k"],
        "properties": {
            "p": {"type": "object", "required": ["n"], "properties": {"n": {"type": "string"}},
                  "nullable": True},
            "k": {"enum": ["x"], "type": "string"},
            "ps": {"type": "array", "items": {"type": "object", "required": ["n"],
                                              "properties": {"n": {"type": "string"}}}},
        },
    }  # fmt: skip


# --- extractor ---


def response(payload, finish=types.FinishReason.STOP):
    return SimpleNamespace(
        text=payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False),
        usage_metadata=SimpleNamespace(prompt_token_count=2500, candidates_token_count=900,
                                       thoughts_token_count=100),
        candidates=[SimpleNamespace(finish_reason=finish)],
    )  # fmt: skip


class FakeClient:
    def __init__(self, *outcomes):
        self.outcomes, self.calls = list(outcomes), []
        self.models = SimpleNamespace(generate_content=self.generate_content)

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def rate_limited():
    return errors.ClientError(429, {"error": {"code": 429, "message": "quota",
                                              "status": "RESOURCE_EXHAUSTED"}})  # fmt: skip


@pytest.fixture
def image() -> bytes:
    page = np.full((900, 700), 255, np.uint8)
    for y in range(80, 800, 40):
        cv2.line(page, (60, y), (640, y), 0, 3)
    return cv2.imencode(".png", page)[1].tobytes()


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    waits = []
    monkeypatch.setattr(gm, "sleep", waits.append)
    return waits


def make(tmp_path, client, **kw):
    return gm.GeminiExtractor(
        client=client,
        model="gemini-test",
        price_input_per_mtok=Decimal(0),  # free tier
        price_output_per_mtok=Decimal(0),
        cache_dir=tmp_path / "cache",
        budget=Budget(tmp_path / "spend.json", Decimal("1"), today=lambda: date(2026, 10, 16)),
        **kw,
    )


def test_valid_answer_becomes_the_document(tmp_path, image):
    client = FakeClient(response({**answer(), "handwritten": True}))
    result = make(tmp_path, client).extract(image, "khatian")
    assert result.error is None and isinstance(result.document, KhatianData)
    assert result.handwritten is True and "handwritten" not in result.document.model_dump()
    assert result.document.khatian_no == "882"
    call = client.calls[0]
    assert call["model"] == "gemini-test"
    config = call["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_schema == gm.gemini_schema("khatian")
    m = result.meta
    assert (m.input_tokens, m.output_tokens, m.cost_usd, m.cached) == (2500, 1000, 0.0, False)


@pytest.mark.parametrize(
    "bad",
    [
        response("not json"),
        response({"doc_type": "khatian", "khatian_no": 882}),
        response(answer(), finish=types.FinishReason.MAX_TOKENS),
        response({**answer(), "owners": [{**answer()["owners"][0], "nid": "1987654321098"}]}),
    ],
)
def test_bad_answers_are_errors_not_exceptions(tmp_path, image, bad):
    result = make(tmp_path, FakeClient(bad)).extract(image, "khatian")
    assert result.document is None and result.error


def test_rate_limit_backs_off_and_retries(tmp_path, image, no_sleep):
    client = FakeClient(rate_limited(), rate_limited(), response(answer()))
    result = make(tmp_path, client).extract(image, "khatian")
    assert result.document is not None and len(client.calls) == 3
    assert no_sleep == [gm.BACKOFF_S, gm.BACKOFF_S * 2]


def test_rate_limit_that_does_not_end_is_an_error_and_not_cached(tmp_path, image, monkeypatch):
    monkeypatch.setattr(settings, "gemini_max_retries", 2)
    client = FakeClient(rate_limited())
    extractor = make(tmp_path, client)
    result = extractor.extract(image, "khatian")
    assert result.document is None and result.error == "api: ClientError 429"
    assert len(client.calls) == 3
    assert not (tmp_path / "cache").exists()  # a later run may succeed


def test_cache_hit_and_provider_in_the_key(tmp_path, image):
    client = FakeClient(response(answer()))
    extractor = make(tmp_path, client)
    extractor.extract(image, "khatian")
    second = extractor.extract(image, "khatian")
    assert second.meta.cached and len(client.calls) == 1
    anthropic = AnthropicExtractor(model="gemini-test", price_input_per_mtok=Decimal(0),
                                   price_output_per_mtok=Decimal(0), cache_dir=tmp_path / "cache",
                                   budget=extractor.budget)  # fmt: skip
    assert anthropic.cache_key(image, "khatian") != extractor.cache_key(image, "khatian")


def test_provider_setting_picks_the_extractor(monkeypatch, tmp_path):
    common = {"model": "m", "price_input_per_mtok": Decimal(0), "price_output_per_mtok": Decimal(0),
              "budget": Budget(tmp_path / "s.json", Decimal(1))}  # fmt: skip
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    assert isinstance(make_llm_extractor(**common), gm.GeminiExtractor)
    monkeypatch.setattr(settings, "llm_provider", "anthropic")
    assert isinstance(make_llm_extractor(**common), AnthropicExtractor)
    monkeypatch.setattr(settings, "llm_provider", "other")
    with pytest.raises(ValueError, match="LLM_PROVIDER"):
        make_llm_extractor(**common)


def test_missing_gemini_model_refuses_to_start(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "gemini_model", None)
    with pytest.raises(ValueError, match="GEMINI_MODEL"):
        gm.GeminiExtractor(price_input_per_mtok=Decimal(0), price_output_per_mtok=Decimal(0),
                           budget=Budget(tmp_path / "s.json", Decimal(1)))  # fmt: skip
