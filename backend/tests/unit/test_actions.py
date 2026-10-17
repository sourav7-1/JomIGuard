import string
import uuid
from pathlib import Path

import pytest
from conftest import TestSession
from scenario_loader import load_scenario

from app.models import DocStatus, DocType, Document, Extraction, ExtractionStatus
from app.services.actions import (
    ALWAYS_ACTIONS,
    FINDING_ACTIONS,
    MAX_ACTIONS,
    REVIEW_ACTION,
    UPLOAD_ACTION,
    next_actions,
)
from app.services.risk import assess, forbidden_words_in
from app.services.rules import run_rules
from app.services.rules.codes import CODES
from app.services.rules.messages import render

SCENARIOS = Path(__file__).parents[1] / "scenarios"
ALL = sorted(p for p in SCENARIOS.iterdir() if p.is_dir())
ALWAYS_IDS = [a[0] for a in ALWAYS_ACTIONS]


def actions_for(folder: Path):
    case, _ = load_scenario(folder)
    run = run_rules(case)
    return next_actions(case, run, assess(case, run))


def test_demo_actions_in_priority_order():
    actions = actions_for(SCENARIOS / "01_demo_area_exceeds")
    ids = [a.id for a in actions]
    wanted = ("ask_seller_shortfall", "get_co_owner_consent", "amin_field_survey")
    ask, consent, amin = (ids.index(i) for i in wanted)
    assert ask < consent < amin
    assert "রহিম উদ্দিন" in actions[ask].text_bn and "৪ শতাংশ" in actions[ask].text_bn
    text = actions[consent].text_bn
    assert "করিম উদ্দিন" in text and "সালমা খাতুন" in text and "আমমোক্তারনামা" in text
    assert actions[ask].priority == 1 and actions[ask].sources


def test_low_risk_scenario_still_has_the_always_actions():
    ids = [a.id for a in actions_for(SCENARIOS / "02_sells_within_share")]
    assert all(i in ids for i in ALWAYS_IDS)


@pytest.mark.parametrize("folder", ALL, ids=lambda p: p.name)
def test_at_most_six_with_always_actions_and_no_forbidden_words(folder):
    actions = actions_for(folder)
    assert len(actions) <= MAX_ACTIONS
    assert [a.id for a in actions][-2:] == ALWAYS_IDS
    assert len({a.text_bn for a in actions}) == len(actions)  # deduped
    for a in actions:
        assert forbidden_words_in(a.text_bn) == [] and a.who in {
            "buyer", "seller", "amin", "lawyer", "land_office"}  # fmt: skip


def test_every_finding_code_has_an_action():
    assert set(FINDING_ACTIONS) == set(CODES)


def test_templates_never_contain_forbidden_words():
    specs = [*FINDING_ACTIONS.values(), UPLOAD_ACTION, REVIEW_ACTION, *ALWAYS_ACTIONS]
    for _, priority, _, template in specs:
        names = {n for _, n, _, _ in string.Formatter().parse(template) if n}
        assert forbidden_words_in(render(template, dict.fromkeys(names, "১০"))) == []
        assert priority in (1, 2, 3)


def test_coverage_gap_asks_for_the_document():
    texts = [a.text_bn for a in actions_for(SCENARIOS / "02_sells_within_share")]
    assert "এই কাগজটি upload করুন: পুরোনো খতিয়ান।" in texts


# --- API ---


def add_document(db, land_id, data: dict, doc_type: DocType):
    doc_id = uuid.uuid4()
    db.add(Document(id=doc_id, land_id=land_id, doc_type=doc_type, status=DocStatus.done,
                    file_key=f"{doc_id}/x.png", original_filename="x.png"))  # fmt: skip
    db.flush()
    db.add(Extraction(document_id=doc_id, extractor="fake", status=ExtractionStatus.ok,
                      data=data, warnings=[], field_flags={}))  # fmt: skip
    db.commit()


def test_assess_endpoint_stores_and_returns(client):
    import json

    land_id = client.post("/lands", json={"mouza": "চাঁদশী", "dag_no": "305"}).json()["id"]
    demo = SCENARIOS / "01_demo_area_exceeds"
    with TestSession() as db:
        for name, doc_type in [("khatian_bs.json", DocType.khatian), ("deed.json", DocType.deed),
                               ("heir_cert.json", DocType.heir_cert)]:  # fmt: skip
            data = json.loads((demo / name).read_text(encoding="utf-8"))
            add_document(db, uuid.UUID(land_id), data, doc_type)
    r = client.post(f"/lands/{land_id}/assess")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["risk_level"] == "high" and body["land_id"] == land_id
    assert {f["code"] for f in body["findings"]} == {"area_exceeds_share", "heir_consent_missing"}
    assert body["actions"] and body["disclaimer_bn"]
    latest = client.get(f"/lands/{land_id}/assessments/latest").json()
    assert latest["id"] == body["id"]
    assert client.get(f"/lands/{uuid.uuid4()}/assessments/latest").status_code == 404
    assert client.post(f"/lands/{uuid.uuid4()}/assess").status_code == 404
