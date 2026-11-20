"""Satellite check: geometry endpoint, queueing, latest, and run_check. No network, no Celery."""

import uuid
from unittest.mock import Mock

import httpx
import pytest
from conftest import TestSession

from app.api import lands as lands_api
from app.models import Land, SatelliteCheck, SatelliteCheckStatus, User
from app.services import satellite
from app.services.satellite import SatelliteServiceError, request_analysis, run_check

RING = [[90.41, 23.99], [90.412, 23.99], [90.412, 23.992], [90.41, 23.992], [90.41, 23.99]]
POLYGON = {"type": "Polygon", "coordinates": [RING]}
RESULT = {"scope": "surroundings", "buffer_m": 200.0, "years": [], "trends": {}, "signals": {}}


@pytest.fixture
def enqueue(monkeypatch):
    delay = Mock()
    monkeypatch.setattr(lands_api.run_satellite_check_task, "delay", delay)
    return delay


def new_land(client, geometry=None) -> str:
    land_id = client.post("/lands", json={"mouza": "ডেমো", "dag_no": "305/1"}).json()["id"]
    if geometry:
        assert client.put(f"/lands/{land_id}/geometry", json=geometry).status_code == 200
    return land_id


def test_put_geometry_saves_and_returns_it(client):
    land_id = new_land(client)
    r = client.put(f"/lands/{land_id}/geometry", json=POLYGON)
    assert r.status_code == 200
    assert r.json()["geometry"] == POLYGON
    assert client.get(f"/lands/{land_id}").json()["geometry"] == POLYGON


@pytest.mark.parametrize(
    "geometry",
    [
        {"type": "Point", "coordinates": [90.41, 23.99]},
        {"type": "Polygon", "coordinates": [RING[:-1]]},  # not closed
        {
            "type": "Polygon",
            "coordinates": [[[77.2, 28.6], [77.3, 28.6], [77.3, 28.7], [77.2, 28.6]]],
        },
        {
            "type": "Polygon",
            "coordinates": [[[90.4, 23.9], [90.42, 23.9], [90.42, 23.92], [90.4, 23.9]]],
        },
    ],
)
def test_put_geometry_rejects_bad_polygons(client, geometry):
    land_id = new_land(client)
    assert client.put(f"/lands/{land_id}/geometry", json=geometry).status_code == 422
    assert client.get(f"/lands/{land_id}").json()["geometry"] is None


def test_other_users_land_is_404_and_anonymous_is_401(client, anonymous_client, enqueue):
    with TestSession() as db:
        other = User(username=f"other-sat-{uuid.uuid4().hex[:6]}", password_hash="unused")
        db.add(other)
        db.flush()
        land = Land(
            owner_id=other.id,
            district="",
            upazila="",
            mouza="x",
            dag_no="1",
            khatian_no="",
            geometry=POLYGON,
        )
        db.add(land)
        db.commit()
        land_id = land.id
    assert client.put(f"/lands/{land_id}/geometry", json=POLYGON).status_code == 404
    assert client.post(f"/lands/{land_id}/satellite-check").status_code == 404
    assert client.get(f"/lands/{land_id}/satellite-check/latest").status_code == 404
    assert anonymous_client.post(f"/lands/{land_id}/satellite-check").status_code == 401
    enqueue.assert_not_called()


def test_start_check_without_geometry_is_409(client, enqueue):
    land_id = new_land(client)
    r = client.post(f"/lands/{land_id}/satellite-check")
    assert r.status_code == 409
    assert "সীমানা" in r.json()["detail"]
    enqueue.assert_not_called()


def test_start_check_queues_after_commit_and_latest_returns_it(client, enqueue):
    land_id = new_land(client, POLYGON)
    assert client.get(f"/lands/{land_id}/satellite-check/latest").status_code == 404

    def committed(check_id):
        with TestSession() as db:  # a separate session sees the row only after the commit
            assert db.get(SatelliteCheck, uuid.UUID(check_id)) is not None

    enqueue.side_effect = committed
    r = client.post(f"/lands/{land_id}/satellite-check", json={"years": [2019, 2025]})
    assert r.status_code == 202
    body = r.json()
    assert body["status"] == "pending" and body["years"] == [2019, 2025] and body["buffer_m"] == 200
    enqueue.assert_called_once_with(body["id"])

    latest = client.get(f"/lands/{land_id}/satellite-check/latest").json()
    assert latest["id"] == body["id"] and latest["status"] == "pending"


def _pending_check(geometry=POLYGON) -> uuid.UUID:
    with TestSession.begin() as db:
        land = Land(
            district="", upazila="", mouza="x", dag_no="1", khatian_no="", geometry=geometry
        )
        db.add(land)
        db.flush()
        check = SatelliteCheck(land_id=land.id, years=None)
        db.add(check)
        db.flush()
        return check.id


def test_run_check_stores_result():
    check_id = _pending_check()
    calls = []

    def post(geometry, buffer_m, years):
        calls.append((geometry, buffer_m, years))
        return RESULT

    with TestSession() as db:
        check = run_check(db, check_id, post=post)
        assert check.status == SatelliteCheckStatus.ok and check.result == RESULT
    assert calls == [(POLYGON, 200.0, None)]

    with TestSession() as db:  # a redelivered task does not run it again
        run_check(db, check_id, post=Mock(side_effect=AssertionError("must not be called")))


def test_run_check_stores_bangla_error_on_failure():
    check_id = _pending_check()
    with TestSession() as db:
        check = run_check(db, check_id, post=Mock(side_effect=SatelliteServiceError("HTTP 503")))
        assert check.status == SatelliteCheckStatus.failed
        assert check.error.startswith(satellite.SERVICE_ERROR_BN) and "HTTP 503" in check.error


def test_run_check_without_geometry_fails():
    check_id = _pending_check(geometry=None)
    with TestSession() as db:
        check = run_check(db, check_id, post=Mock())
        assert check.status == SatelliteCheckStatus.failed
        assert check.error == satellite.NO_GEOMETRY_BN


def _fake_post(monkeypatch, response=None, error=None):
    sent = {}

    def fake(url, json, timeout):
        sent.update(url=url, json=json, timeout=timeout)
        if error:
            raise error
        return response

    monkeypatch.setattr(satellite.httpx, "post", fake)
    return sent


def test_request_analysis_ok(monkeypatch):
    sent = _fake_post(monkeypatch, httpx.Response(200, json={"success": True, "result": RESULT}))
    assert request_analysis(POLYGON, 200.0, [2019, 2025]) == RESULT
    assert sent["url"].endswith("/api/analyze-area")
    assert sent["json"] == {"geometry": POLYGON, "buffer_m": 200.0, "years": [2019, 2025]}
    assert sent["timeout"] >= 300


def test_request_analysis_leaves_out_years_when_not_given(monkeypatch):
    sent = _fake_post(monkeypatch, httpx.Response(200, json={"success": True, "result": RESULT}))
    request_analysis(POLYGON, 200.0, None)
    assert "years" not in sent["json"]


@pytest.mark.parametrize(
    "response, error, expected",
    [
        (
            httpx.Response(400, json={"success": False, "message": "bad polygon"}),
            None,
            "bad polygon",
        ),
        (httpx.Response(500, text="boom"), None, "HTTP 500"),
        (None, httpx.ConnectError("refused"), "ConnectError"),
        (None, httpx.ReadTimeout("slow"), "ReadTimeout"),
    ],
)
def test_request_analysis_errors(monkeypatch, response, error, expected):
    _fake_post(monkeypatch, response, error)
    with pytest.raises(SatelliteServiceError, match=expected):
        request_analysis(POLYGON, 200.0, None)


HEAVY = {
    "buffer_m": 200.0,
    "years": [
        {"year": y, "status": "ok", "low_confidence": False, "metrics": {"water_pct": 30.0}}
        for y in range(2019, 2026)
    ],
    "trends": {},
    "signals": {"water_heavy_years": [2022], "water_spike_years": [], "outlier_years": []},
}


def test_assessment_adds_satellite_group_without_changing_risk(client):
    land_id = new_land(client, POLYGON)
    before = client.post(f"/lands/{land_id}/assess").json()
    assert before["satellite_findings"] == [] and before["satellite_check_id"] is None

    with TestSession.begin() as db:
        check = SatelliteCheck(
            land_id=uuid.UUID(land_id), status=SatelliteCheckStatus.ok, result=HEAVY
        )
        db.add(check)
        db.flush()
        check_id = str(check.id)

    after = client.post(f"/lands/{land_id}/assess").json()
    assert after["risk_level"] == before["risk_level"]
    assert after["findings"] == before["findings"] and after["summary_bn"] == before["summary_bn"]
    assert after["satellite_check_id"] == check_id
    assert [f["rule_id"] for f in after["satellite_findings"]] == ["satellite_water_dry_season"]
    assert after["satellite_findings"][0]["group"] == "satellite"

    latest = client.get(f"/lands/{land_id}/satellite-check/latest").json()
    assert latest["status"] == "ok" and latest["group_title_bn"] == "স্যাটেলাইট যাচাই"
    assert [f["rule_id"] for f in latest["findings"]] == ["satellite_water_dry_season"]
    assert "২০০ মিটার" in latest["area_note_bn"]


def test_failed_check_is_not_used_by_assessment(client):
    land_id = new_land(client, POLYGON)
    with TestSession.begin() as db:
        db.add(
            SatelliteCheck(
                land_id=uuid.UUID(land_id), status=SatelliteCheckStatus.failed, error="x"
            )
        )
    assert client.post(f"/lands/{land_id}/assess").json()["satellite_findings"] == []
    latest = client.get(f"/lands/{land_id}/satellite-check/latest").json()
    assert latest["status"] == "failed" and latest["findings"] == []


def test_satellite_task_has_its_own_queue_and_documents_keep_the_default():
    from app.workers.celery_app import celery_app

    def queue(task):
        return celery_app.amqp.router.route({}, f"app.workers.tasks.{task}")["queue"].name

    assert queue("run_satellite_check_task") == "satellite"
    assert queue("process_document_task") == celery_app.conf.task_default_queue == "celery"
