"""Journey gating and the safety rule: a no-mismatch headline never shows while any document is
unread or pending, the assessment is stale, or checks were skipped."""

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from conftest import TestSession
from scenario_loader import load_scenario

from app.models import DocStatus, DocType, Document, LandAssessment, SatelliteCheck
from app.models.document import DocStep
from app.services.journey import JourneyInput, build_journey, safe_headline
from app.services.risk import HEADLINES_BN, assess
from app.services.rules import run_rules

SCENARIOS = Path(__file__).parents[1] / "scenarios"
LOW = {"risk_level": "low", "headline_bn": HEADLINES_BN["low"], "coverage": {},
       "actions": [{"text_bn": "আমিন দিয়ে জমি মাপান", "done": False}]}  # fmt: skip


def status(j, n):
    return j.steps[n - 1].status


def test_low_headline_kept_only_when_everything_was_checked():
    j = build_journey(JourneyInput(doc_statuses=["done", "done"], assessment=LOW))
    assert j.incomplete_reasons_bn == []
    assert safe_headline(LOW, j) == HEADLINES_BN["low"]


def test_unread_document_replaces_the_low_headline():  # the case 36eb3095 bug
    j = build_journey(JourneyInput(doc_statuses=["done", "failed", "failed"], assessment=LOW))
    headline = safe_headline(LOW, j)
    assert headline != HEADLINES_BN["low"] and "অমিল পাওয়া যায়নি" not in headline
    assert "২টি কাগজ পড়া যায়নি" in headline
    assert status(j, 2) == "action" and status(j, 3) == "action" and status(j, 5) == "locked"


def test_pending_stale_and_skipped_are_incomplete():
    pending = build_journey(JourneyInput(doc_statuses=["done", "processing"], assessment=LOW))
    stale = build_journey(
        JourneyInput(doc_statuses=["done"], assessment=LOW, assessment_stale=True)
    )
    skipped_low = {**LOW, "coverage": {"checks_skipped": [{"rule_id": "x", "reason_bn": "-"}],
                                       "documents_missing_bn": ["বিক্রয় দলিল"]}}  # fmt: skip
    skipped = build_journey(JourneyInput(doc_statuses=["done"], assessment=skipped_low))
    for j, low in ((pending, LOW), (stale, LOW), (skipped, skipped_low)):
        assert j.incomplete_reasons_bn and safe_headline(low, j) != HEADLINES_BN["low"]
    assert "কেসে নেই: বিক্রয় দলিল" in skipped.incomplete_reasons_bn
    assert status(pending, 3) == "waiting" and status(stale, 3) == "action"


def test_high_and_medium_headlines_are_never_softened():
    high = {**LOW, "risk_level": "high", "headline_bn": HEADLINES_BN["high"]}
    j = build_journey(JourneyInput(doc_statuses=["failed"], assessment=high))
    assert safe_headline(high, j) == HEADLINES_BN["high"]


def test_steps_are_gated_in_order():
    # satellite done but papers not checked: the report must not count as done (old tracker bug)
    j = build_journey(JourneyInput(doc_statuses=["done"], has_geometry=True, satellite_status="ok"))
    assert [s.status for s in j.steps[:5]] == ["done", "done", "action", "done", "locked"]
    assert j.progress_done == 3 and j.progress_total == 5
    no_plot = build_journey(JourneyInput())
    assert status(no_plot, 4) == "locked" and "সীমানা" in no_plot.steps[3].note_bn
    assert status(no_plot, 3) == "locked" and status(no_plot, 2) == "action"
    full = build_journey(JourneyInput(doc_statuses=["done"], has_geometry=True,
                                      satellite_status="ok", assessment=LOW))  # fmt: skip
    assert full.progress_done == 5 and status(full, 6) == "todo"
    assert [s.phase for s in full.steps] == ["before"] * 5 + ["during"] * 2 + ["after"]


def test_next_action_blocker_first_then_assessment_action():
    blocked = build_journey(JourneyInput(doc_statuses=["failed"], assessment=LOW))
    assert "পড়া যায়নি" in blocked.next_action_bn
    ok = build_journey(JourneyInput(doc_statuses=["done"], assessment=LOW))
    assert ok.next_action_bn == "আমিন দিয়ে জমি মাপান"
    assert build_journey(JourneyInput()).next_action_bn  # empty case still says what to do


# --- API: case-view headline and the dashboard summary on GET /lands ---


def _low_result() -> dict:
    case, _ = load_scenario(SCENARIOS / "02_sells_within_share")
    result = assess(case, run_rules(case)).model_dump(mode="json")
    # pretend every check ran, so the only gap is the unread document below
    result["coverage"] = {**result["coverage"], "complete": True, "checks_skipped": [],
                          "documents_missing": [], "documents_missing_bn": []}  # fmt: skip
    result["headline_bn"] = HEADLINES_BN["low"]
    return result


def test_case_view_and_list_never_show_no_mismatch_with_unread_document(client):
    land_id = uuid.UUID(client.post("/lands", json={"mouza": "বিরুলিয়া", "dag_no": "৪১৭",
                                                     "district": "ঢাকা"}).json()["id"])  # fmt: skip
    with TestSession() as db:
        db.add(Document(id=uuid.uuid4(), land_id=land_id, doc_type=DocType.deed,
                        status=DocStatus.failed, current_step=DocStep.finished,
                        file_key="d.png", original_filename="2-deed.png"))  # fmt: skip
        db.add(LandAssessment(land_id=land_id, engine_version="t", risk_level="low",
                              result=_low_result()))  # fmt: skip
        db.commit()

    cv = client.get(f"/lands/{land_id}/case-view").json()
    headline = cv["latest_assessment"]["headline_bn"]
    assert headline != HEADLINES_BN["low"] and "১টি কাগজ পড়া যায়নি" in headline
    assert "নিরাপদ" not in cv["latest_assessment"]["disclaimer_bn"]
    assert cv["journey"]["steps"][1]["status"] == "action"
    assert cv["journey"]["incomplete_reasons_bn"][0] == "১টি কাগজ পড়া যায়নি"

    [item] = [x for x in client.get("/lands").json() if x["id"] == str(land_id)]
    summary = item["summary"]
    assert summary["risk_level"] == "low" and summary["complete"] is False
    assert summary["progress_total"] == 5 and summary["progress_done"] == 0
    assert "পড়া যায়নি" in summary["next_action_bn"]
    assert datetime.fromisoformat(summary["updated_at"]) > datetime.now(UTC) - timedelta(hours=1)


def test_list_summary_counts_satellite_and_plot(client):
    land_id = uuid.UUID(
        client.post("/lands", json={"mouza": "চর মেঘনা", "dag_no": "১"}).json()["id"]
    )
    with TestSession() as db:
        from app.models import Land

        land = db.get(Land, land_id)
        land.geometry = {"type": "Polygon", "coordinates": []}
        db.add(SatelliteCheck(land_id=land_id, status="ok"))
        db.commit()
    [item] = [x for x in client.get("/lands").json() if x["id"] == str(land_id)]
    assert item["summary"]["progress_done"] == 2  # plot outline + satellite; no papers yet
    assert item["summary"]["risk_level"] is None and item["summary"]["complete"] is False
