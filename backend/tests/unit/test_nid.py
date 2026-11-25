"""NID name reading (docs/specs/identity.md): only the three name fields ever leave the reader,
the image is never stored, and the names feed the seller_identity rule.

Only synthetic cards: tests/fixtures/nid/ is made by ml/synth/nid.py (watermarked
"নমুনা / SAMPLE", placeholder ID number and birth date). Providers are mocked; no network.
"""

import json
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest
from conftest import TestSession
from pydantic import SecretStr
from scenario_loader import load_scenario
from test_identity import SCENARIO, _create_link, _land_with_case

from app.core.config import settings
from app.models import IdentityVerification
from app.schemas.land_case import IdentityCaseResult
from app.services.extraction import gemini as gm
from app.services.identity import nid
from app.services.risk import assess
from app.services.rules import RULES, Status, run_rules
from app.services.rules.messages import OCR_UNVERIFIED_TITLE

FIXTURE = Path(__file__).parents[1] / "fixtures/nid"
CARD = (FIXTURE / "nid_001.png").read_bytes()
CARD_TRUTH = json.loads((FIXTURE / "nid_001.json").read_text(encoding="utf-8"))
# what a careless model might send back; none of it may survive
FORBIDDEN = {
    "nid_no": "0000000000",
    "date_of_birth": "1900-01-01",
    "address": "নমুনা ঠিকানা",
    "blood_group": "O+",
    "signature": "নমুনা স্বাক্ষর",
    "photo": "a face",
    "mother_name": "নমুনা মাতা",
}
FORBIDDEN_TEXT = ("0000000000", "1900", "নমুনা ঠিকানা", "O+", "নমুনা স্বাক্ষর", "নমুনা মাতা")


def reader(names: dict | None, source="ai"):
    """nid_steps() replacement: one step returning `names` (+ forbidden extras) via parse_names."""
    return lambda: [(source, lambda img: nid.parse_names({**FORBIDDEN, **(names or {})}))]


def seller_of_case():
    case, _ = load_scenario(SCENARIO)
    return case.proposed_deed.data.sellers[0]


def upload(client, token, outcome="verified"):
    return client.post(
        f"/verify/{token}/nid",
        files={"image": ("card.png", CARD, "image/png")},
        data={"outcome": outcome},
    )


def consented_link(client):
    land_id, case = _land_with_case(client)
    token = _create_link(client, land_id, case.proposed_deed.data.sellers[0].name)
    assert client.post(f"/verify/{token}/consent", json={"consent": True}).status_code == 200
    return land_id, token


# --- 1. forbidden fields are never returned or stored ---


def test_parse_names_keeps_only_the_three_name_fields():
    names = nid.parse_names({**FORBIDDEN, "name_bn": " মোঃ রহিম ", "name_en": "RAHIM"})
    assert set(names.model_dump()) == {"name_bn", "name_en", "father_or_husband_name"}
    assert names.name_bn == "মোঃ রহিম" and names.father_or_husband_name is None
    assert nid.parse_names("not a dict") == nid.NidNames()


def test_forbidden_fields_never_reach_the_db_the_api_or_the_log(
    client, storage, monkeypatch, caplog
):
    seller = seller_of_case()
    names = {"name_bn": seller.name, "father_or_husband_name": seller.father_or_husband_name}
    monkeypatch.setattr(nid, "nid_steps", reader(names))
    land_id, token = consented_link(client)
    with caplog.at_level(logging.INFO):
        r = upload(client, token)
    assert r.status_code == 200, r.text
    body = r.text
    assert not any(text in body for text in FORBIDDEN_TEXT)
    assert not set(FORBIDDEN) & set(r.json())
    with TestSession() as db:
        row = db.query(IdentityVerification).filter_by(land_id=land_id).one()
        stored = " ".join(str(getattr(row, c.key)) for c in row.__table__.columns)
    assert not any(text in stored for text in FORBIDDEN_TEXT)
    # audit line: what happened, no names
    [line] = [r.getMessage() for r in caplog.records if "identity.nid_read" in r.getMessage()]
    assert "party=seller" in line and "result=matched" in line and seller.name not in line
    assert storage.objects == {}  # 2. the image never went to MinIO


# --- 2. the image is not kept anywhere ---


def test_ai_reader_uses_no_cache_and_the_image_is_not_written(tmp_path):
    """The Anthropic step reads with a fake client; nothing lands in the extraction cache."""
    tool = SimpleNamespace(type="tool_use", name=nid.TOOL_NAME,
                           input={**FORBIDDEN, "name_bn": "রহিম উদ্দিন"})  # fmt: skip
    answer = SimpleNamespace(stop_reason="tool_use", content=[tool],
                             usage=SimpleNamespace(input_tokens=10, output_tokens=5))  # fmt: skip
    client = SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: answer))
    from decimal import Decimal

    from app.services.extraction import Budget

    ai = nid.AnthropicNidReader(
        client=client, model="claude-test", cache_dir=tmp_path / "cache",
        price_input_per_mtok=Decimal(0), price_output_per_mtok=Decimal(0),
        budget=Budget(tmp_path / "spend.json", Decimal(1)),
    )  # fmt: skip
    names = ai.read(CARD)
    assert names == nid.NidNames(name_bn="রহিম উদ্দিন")
    assert not (tmp_path / "cache").exists()


# --- 3. match / partial / no match / unreadable ---


@pytest.mark.parametrize(
    ("name", "father", "expected"),
    [
        ("SAME", "SAME", "matched"),
        ("SAME", "করিম মিয়া", "partial"),  # name matches, father/husband differs
        ("জমির আলী", None, "no_match"),
    ],
)
def test_seller_nid_results(client, monkeypatch, name, father, expected):
    seller = seller_of_case()
    name = seller.name if name == "SAME" else name
    father = seller.father_or_husband_name if father == "SAME" else father
    monkeypatch.setattr(
        nid, "nid_steps", reader({"name_bn": name, "father_or_husband_name": father})
    )
    land_id, token = consented_link(client)
    r = upload(client, token)
    assert r.status_code == 200, r.text
    assert r.json()["match_result"] == expected and r.json()["name_source"] == "ai"
    assert upload(client, token).status_code == 410  # the link is used up

    codes = {
        "matched": set(),
        "partial": {"seller_nid_name_partial"},
        "no_match": {"seller_nid_name_mismatch"},
    }
    assessment = client.post(f"/lands/{land_id}/assess").json()
    found = {f["code"] for f in assessment["findings"] if f["rule_id"] == "seller_identity"}
    assert found == codes[expected]


def test_unreadable_photo_keeps_the_link_for_another_try(client, monkeypatch):
    monkeypatch.setattr(nid, "nid_steps", lambda: [("ai", lambda img: nid.NidNames())])
    land_id, token = consented_link(client)
    r = upload(client, token)
    assert r.status_code == 200 and r.json()["match_result"] == "unreadable"
    assert r.json()["status"] == "pending" and r.json()["name_bn_as_per_nid"] is None
    seller = seller_of_case()
    monkeypatch.setattr(nid, "nid_steps", reader({"name_bn": seller.name}))
    assert upload(client, token).json()["match_result"] == "matched"  # same link works


def test_consent_is_needed_before_reading(client, monkeypatch):
    monkeypatch.setattr(nid, "nid_steps", lambda: pytest.fail("read before consent"))
    land_id, case = _land_with_case(client)
    token = _create_link(client, land_id, case.proposed_deed.data.sellers[0].name)
    assert upload(client, token).status_code == 409


def test_oversized_image_is_refused(client, monkeypatch):
    monkeypatch.setattr(nid, "MAX_IMAGE_BYTES", 10)
    monkeypatch.setattr("app.api.identity.MAX_IMAGE_BYTES", 10)
    _, token = consented_link(client)
    assert upload(client, token).status_code == 413


# --- 4. the OCR path ---


def test_ocr_reads_only_the_names_of_the_sample_card():
    names = nid.ocr_read(CARD)  # real Tesseract on the synthetic card
    assert names.model_dump() == CARD_TRUTH
    assert not any(t in json.dumps(names.model_dump()) for t in ("1900", "0000", "মাতা"))


def test_ocr_chain_marks_the_read_and_never_uses_gemini(monkeypatch):
    # even with Gemini as the main provider and a key set, it is never a step for an NID
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", SecretStr("test-key"))
    monkeypatch.setattr(settings, "anthropic_api_key", None)
    monkeypatch.setattr(gm.GeminiExtractor, "__init__", lambda *a, **k: pytest.fail("Gemini"))
    assert [name for name, _ in nid.nid_steps()] == ["ai", "ocr"]
    read = nid.read_nid(CARD)  # ai step: no Anthropic key -> skipped; ocr reads it
    assert read.source == "ocr" and read.names.name_bn == CARD_TRUTH["name_bn"]


def test_ocr_read_nid_name_goes_to_verify_not_a_mismatch():
    case, _ = load_scenario(SCENARIO)
    seller = case.proposed_deed.data.sellers[0]

    def run(source):
        row = IdentityCaseResult(party="seller", seller_name_on_deed=seller.name,
                                 status="verified", name_bn_as_per_nid="জমির আলী",
                                 name_source=source)  # fmt: skip
        c = case.model_copy(update={"identity": [row]})
        return c, run_rules(c)

    _, ai = run("ai")
    assert "seller_nid_name_mismatch" in {f.code for f in ai.findings}
    c, ocr = run("ocr")
    assert "seller_nid_name_mismatch" not in {f.code for f in ocr.findings}
    [item] = [r for r in ocr.to_verify if r.rule_id == "seller_identity"]
    assert item.status == Status.skipped and item.title_bn == OCR_UNVERIFIED_TITLE
    assert item.values["ocr_original_code"] == "seller_nid_name_mismatch"
    without = assess(c, run_rules(c, [r for r in RULES if r != "seller_identity"])).risk_level
    assert assess(c, ocr).risk_level == without  # an OCR name adds no risk


# --- 5. buyer: result card against the deed buyers of the user's own cases ---


def test_buyer_nid_matches_the_deed_buyers_and_needs_consent(client, monkeypatch):
    _, case = _land_with_case(client)
    buyer = case.proposed_deed.data.buyers[0]
    monkeypatch.setattr(nid, "nid_steps", reader({"name_bn": buyer.name}))
    files = {"image": ("card.png", CARD, "image/png")}
    refused = client.post("/me/verification/nid", files=files, data={"consent": "false"})
    assert refused.status_code == 422
    r = client.post("/me/verification/nid", files=files, data={"consent": "true"})
    assert r.status_code == 201, r.text
    assert r.json()["party"] == "buyer" and r.json()["match_result"] == "matched"
    assert not any(text in r.text for text in FORBIDDEN_TEXT)
    with TestSession() as db:
        row = db.get(IdentityVerification, r.json()["id"])
        assert row.consent_version == "identity-nid-name-v1"
