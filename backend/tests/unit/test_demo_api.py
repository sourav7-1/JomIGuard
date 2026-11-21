"""Judge demo: hourly limits, prepared samples stay unchanged, packs make new cases."""

import io
import uuid
import zipfile
from unittest.mock import Mock

import pytest
from conftest import TEST_ADMIN_ID, TestSession

from app.api import demo as demo_api
from app.api import documents as documents_api
from app.api import lands as lands_api
from app.models import Document, Land
from app.services import demo_guard, demo_packs

RING = [[90.41, 23.99], [90.412, 23.99], [90.412, 23.992], [90.41, 23.992], [90.41, 23.99]]
POLYGON = {"type": "Polygon", "coordinates": [RING]}


@pytest.fixture
def queued(monkeypatch):
    delay = Mock()
    monkeypatch.setattr(lands_api.run_satellite_check_task, "delay", delay)
    monkeypatch.setattr(documents_api.process_document_task, "delay", delay)
    monkeypatch.setattr(demo_api.process_document_task, "delay", delay)
    return delay


def land_with_geometry(client) -> str:
    land_id = client.post("/lands", json={"mouza": "ডেমো", "dag_no": "1"}).json()["id"]
    assert client.put(f"/lands/{land_id}/geometry", json=POLYGON).status_code == 200
    return land_id


def prepared_sample() -> uuid.UUID:
    """A land like demo_reset's: one document stored under the "demo/" prefix."""
    with TestSession() as db:
        land = Land(owner_id=TEST_ADMIN_ID, district="ঢাকা", upazila="", mouza="নমুনা",
                    dag_no="1", khatian_no="", geometry=POLYGON)  # fmt: skip
        db.add(land)
        db.flush()
        db.add(
            Document(
                land_id=land.id,
                owner_id=TEST_ADMIN_ID,
                file_key="demo/x/khatian.png",
                original_filename="khatian.png",
            )
        )
        db.commit()
        return land.id


def test_satellite_checks_are_capped_per_hour(client, queued, monkeypatch):
    land_id = land_with_geometry(client)
    with TestSession() as db:
        used = demo_guard.satellite_checks_last_hour(db, TEST_ADMIN_ID)
    monkeypatch.setattr(demo_guard, "SATELLITE_PER_HOUR", used + 2)
    assert client.post(f"/lands/{land_id}/satellite-check").status_code == 202
    assert client.post(f"/lands/{land_id}/satellite-check").status_code == 202
    r = client.post(f"/lands/{land_id}/satellite-check")
    assert r.status_code == 429
    assert "এক ঘণ্টায়" in r.json()["detail"]
    assert queued.call_count == 2


def test_uploads_are_capped_per_hour(client, queued, monkeypatch):
    with TestSession() as db:
        used = demo_guard.uploads_last_hour(db, TEST_ADMIN_ID)
    monkeypatch.setattr(demo_guard, "UPLOADS_PER_HOUR", used + 1)
    png = {"file": ("a.png", io.BytesIO(b"\x89PNG fake"), "image/png")}
    assert client.post("/documents", files=png).status_code == 201
    png = {"file": ("b.png", io.BytesIO(b"\x89PNG fake"), "image/png")}
    assert client.post("/documents", files=png).status_code == 429
    pack_id = next(iter(demo_packs.packs()))
    assert client.post(f"/demo/packs/{pack_id}/case").status_code == 429


def test_prepared_samples_cannot_be_changed(client, queued):
    land_id = prepared_sample()
    assert client.put(f"/lands/{land_id}/geometry", json=POLYGON).status_code == 403
    r = client.post(f"/lands/{land_id}/satellite-check")
    assert r.status_code == 403
    assert "নমুনা" in r.json()["detail"]
    png = {"file": ("a.png", io.BytesIO(b"\x89PNG fake"), "image/png")}
    assert client.post("/documents", files=png, data={"land_id": str(land_id)}).status_code == 403
    queued.assert_not_called()


def test_pack_case_is_a_new_land_with_the_pack_documents(client, queued, storage):
    packs = client.get("/demo/packs").json()
    assert {p["id"] for p in packs} == {"A", "B", "C", "D", "E"}
    pack = demo_packs.packs()["D"]
    r = client.post("/demo/packs/D/case")
    assert r.status_code == 201
    land = r.json()
    assert land["mouza"] == pack["land"]["mouza"] and land["district"] == pack["land"]["district"]
    with TestSession() as db:
        docs = db.query(Document).filter(Document.land_id == uuid.UUID(land["id"])).all()
        assert sorted(d.doc_type for d in docs) == sorted(f["doc_type"] for f in pack["files"])
        assert all(d.file_key.startswith("pack/") for d in docs)  # not a prepared sample
        assert not demo_guard.is_prepared_sample(db, uuid.UUID(land["id"]))
    assert queued.call_count == len(pack["files"])
    assert client.post("/demo/packs/Z/case").status_code == 404


def test_pack_zip_holds_every_page(client):
    r = client.get("/demo/packs/A.zip")
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
    names = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
    assert {n.rsplit("/", 1)[1] for n in names} >= {
        f["name"] for f in demo_packs.packs()["A"]["files"]
    }


def test_plot_case_has_the_outline(client):
    r = client.post("/demo/plots/gazipur/case")
    assert r.status_code == 201 and r.json()["geometry"]["type"] == "Polygon"
    assert client.post("/demo/plots/nowhere/case").status_code == 404


def test_demo_needs_login(anonymous_client):
    assert anonymous_client.get("/demo/packs").status_code == 401
    assert anonymous_client.post("/demo/packs/A/case").status_code == 401


# --- sample documents for the judge's own case (upload page) -------------------------------

EXPECTED_RISK = {"A": "low", "B": "high", "C": "high", "D": "medium", "E": "low"}


def own_land(client) -> str:
    body = {
        "district": "ঢাকা",
        "upazila": "সাভার",
        "mouza": "বলিয়ারপুর",
        "dag_no": "৪১৭",
        "khatian_no": "123",
    }
    return client.post("/lands", json=body).json()["id"]


@pytest.mark.parametrize("scenario", list(EXPECTED_RISK))
def test_sample_set_is_rendered_for_this_land(client, scenario):
    land_id = own_land(client)
    info = client.get(f"/demo/lands/{land_id}/sample-sets/{scenario}").json()
    assert info["expected"]["risk_level"] == EXPECTED_RISK[scenario]
    types = {f["doc_type"] for f in info["files"]}
    assert {"khatian", "deed", "dcr", "heir_cert"} <= types
    r = client.get(f"/demo/lands/{land_id}/sample-sets/{scenario}/{info['files'][0]['name']}")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert r.content[:4] == b"\x89PNG"


def test_sample_set_uses_the_land_location():
    from types import SimpleNamespace

    from app.services import sample_sets

    land = SimpleNamespace(
        district="ঢাকা", upazila="সাভার", mouza="বলিয়ারপুর", dag_no="৪১৭", khatian_no="123"
    )
    files = {f.doc_type: f.data for f in sample_sets.sample_set(land, "C")}
    assert files["khatian"]["location"]["mouza"] == "বলিয়ারপুর"
    assert files["khatian"]["khatian_no"] == "123"
    assert files["khatian"]["plots"][0]["dag_no"] == "417"
    assert files["deed"]["schedule_plots"][0]["dag_no"] == "418"  # the mismatch
    assert "চাঁদশী" not in str(files) and "গৌরনদী" not in str(files)


def test_single_sample_and_zip(client):
    land_id = own_land(client)
    for kind in ("khatian", "deed", "prior_deed", "dcr", "heir_cert"):
        assert client.get(f"/demo/lands/{land_id}/samples/{kind}.png").status_code == 200
    assert client.get(f"/demo/lands/{land_id}/samples/nid.png").status_code == 404
    z = zipfile.ZipFile(io.BytesIO(client.get(f"/demo/lands/{land_id}/samples.zip").content))
    names = z.namelist()
    assert "README.txt" in names and "A/1-khatian.png" in names and "E/2-deed.png" in names


def test_samples_refused_for_prepared_and_foreign_lands(client):
    sample = prepared_sample()
    r = client.get(f"/demo/lands/{sample}/sample-sets/A")
    assert r.status_code == 403
    assert client.get(f"/demo/lands/{uuid.uuid4()}/samples/khatian.png").status_code == 404
    assert client.get(f"/demo/lands/{own_land(client)}/sample-sets/Z").status_code == 404
