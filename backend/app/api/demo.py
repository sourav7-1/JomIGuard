"""Judge demo: document packs, satellite demo plots, and a read-only status box."""

import io
import uuid
import zipfile
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import authenticated_user
from app.core.config import settings
from app.db.session import get_db
from app.models import Land, SatelliteCheck, SatelliteCheckStatus, User
from app.schemas.land_case import LandOut
from app.services import demo_guard, demo_packs, sample_sets
from app.services.storage import Storage, get_storage
from app.workers.tasks import process_document_task

router = APIRouter(prefix="/demo", tags=["demo"])
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(authenticated_user)]


def _pack(pack_id: str) -> dict:
    pack = demo_packs.packs().get(pack_id)
    if pack is None:
        raise HTTPException(404, "Pack not found")
    return pack


@router.get("/packs")
def list_packs(user: CurrentUser):
    return [
        {"id": p["id"], "scenario": p["scenario"], "files": p["files"], "land": p["land"]}
        for p in demo_packs.packs().values()
    ]


@router.get("/packs/{pack_id}.zip")
def download_pack(pack_id: str, user: CurrentUser):
    _pack(pack_id)
    return Response(
        demo_packs.pack_zip(pack_id),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="jomiguard-sample-{pack_id}.zip"'},
    )


@router.post("/packs/{pack_id}/case", response_model=LandOut, status_code=201)
def pack_case(
    pack_id: str, db: Db, user: CurrentUser, storage: Annotated[Storage, Depends(get_storage)]
):
    """A NEW case owned by the caller, with the pack's documents uploaded and queued."""
    pack = _pack(pack_id)
    if not demo_guard.upload_allowed(db, user.id, len(pack["files"])):
        raise HTTPException(429, demo_guard.UPLOAD_LIMIT_BN)
    land, docs = demo_packs.create_pack_case(db, storage, user, pack_id)
    db.commit()
    for doc in docs:  # only after the commit: the worker must find them
        process_document_task.delay(str(doc.id))
    return land


@router.get("/plots")
def list_plots(user: CurrentUser):
    return [
        {"id": k, "geometry": v["geometry"], "land": v["land"]}
        for k, v in demo_packs.plots().items()
    ]


@router.post("/plots/{plot_id}/case", response_model=LandOut, status_code=201)
def plot_case(plot_id: str, db: Db, user: CurrentUser):
    """A NEW case owned by the caller with the demo plot's outline; start the check separately."""
    if plot_id not in demo_packs.plots():
        raise HTTPException(404, "Plot not found")
    land = demo_packs.create_plot_case(db, user, plot_id)
    db.commit()
    return land


@router.get("/status")
def status(db: Db, user: CurrentUser):
    """Read-only health for the docs page. No URLs, versions or secrets."""
    try:
        sentinel_up = (
            httpx.get(f"{settings.sentinel_url.rstrip('/')}/healthz", timeout=3).status_code == 200
        )
    except httpx.HTTPError:
        sentinel_up = False
    last = db.scalars(
        select(SatelliteCheck).order_by(SatelliteCheck.created_at.desc()).limit(1)
    ).first()
    last_ok = db.scalars(
        select(SatelliteCheck)
        .where(SatelliteCheck.status == SatelliteCheckStatus.ok)
        .order_by(SatelliteCheck.created_at.desc())
        .limit(1)
    ).first()
    return {
        "backend": True,
        "sentinel": sentinel_up,
        # Earth Engine has no cheap ping: report whether the most recent live check succeeded.
        "earth_engine": None if last is None else last.status == SatelliteCheckStatus.ok,
        "last_check_at": last.created_at if last else None,
        "last_ok_at": last_ok.created_at if last_ok else None,
        "satellite_limit_per_hour": demo_guard.SATELLITE_PER_HOUR,
    }


# --- sample documents for the judge's OWN case (upload page) ---------------------------------
# The files are rendered for this land (its mouza, dag, khatian, upazila); the browser then
# uploads them through the normal upload endpoint, so validation and limits are the same.


def _sample_land(db: Session, land_id: uuid.UUID, user: User) -> Land:
    land = db.get(Land, land_id)
    if land is None or land.owner_id != user.id:
        raise HTTPException(404, "Land not found")
    if demo_guard.is_prepared_sample(db, land_id):
        raise HTTPException(403, demo_guard.SAMPLE_LOCKED_BN)
    return land


def _scenario(scenario: str) -> str:
    if scenario not in sample_sets.SCENARIOS:
        raise HTTPException(404, "Scenario not found")
    return scenario


def _png(content: bytes, name: str) -> Response:
    return Response(
        content,
        media_type="image/png",
        headers={
            "Content-Disposition": f'inline; filename="{name}"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/lands/{land_id}/sample-sets/{scenario}")
def sample_set_info(land_id: uuid.UUID, scenario: str, db: Db, user: CurrentUser):
    """The files of one scenario for this land, and the engine's result on their ground truth."""
    files = sample_sets.sample_set(_sample_land(db, land_id, user), _scenario(scenario))
    return {
        "scenario": scenario,
        "files": [{"name": f.name, "doc_type": f.doc_type} for f in files],
        "expected": sample_sets.expected(files),
    }


@router.get("/lands/{land_id}/sample-sets/{scenario}/{name}")
def sample_set_file(land_id: uuid.UUID, scenario: str, name: str, db: Db, user: CurrentUser):
    files = sample_sets.sample_set(_sample_land(db, land_id, user), _scenario(scenario))
    f = next((f for f in files if f.name == name), None)
    if f is None:
        raise HTTPException(404, "File not found")
    return _png(sample_sets.render(f, sample_sets.seed_for(land_id, scenario + name)), name)


@router.get("/lands/{land_id}/samples/{kind}.png")
def single_sample_file(land_id: uuid.UUID, kind: str, db: Db, user: CurrentUser):
    if kind not in sample_sets.SINGLE:
        raise HTTPException(404, "Sample not found")
    f = sample_sets.single_sample(_sample_land(db, land_id, user), kind)
    return _png(sample_sets.render(f, sample_sets.seed_for(land_id, kind)), f.name)


@router.get("/lands/{land_id}/samples.zip")
def samples_zip(land_id: uuid.UUID, db: Db, user: CurrentUser):
    """Every scenario for this land, one folder each, to try drag-and-drop by hand."""
    land = _sample_land(db, land_id, user)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:  # PNGs are already compressed
        z.writestr("README.txt", sample_sets.README)
        for scenario in sample_sets.SCENARIOS:
            for f in sample_sets.sample_set(land, scenario):
                z.writestr(
                    f"{scenario}/{f.name}",
                    sample_sets.render(f, sample_sets.seed_for(land_id, scenario + f.name)),
                )
    return Response(
        buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="jomiguard-samples.zip"'},
    )
