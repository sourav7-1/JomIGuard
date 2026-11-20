"""Satellite check of a land's surroundings via the sentinel service (POST /api/analyze-area).

start_check() stores a pending row; run_check() (called from a Celery task) calls the service and
stores the full response or a Bangla error. The HTTP call is a parameter so tests never need the
network.
"""

import uuid
from collections.abc import Callable

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Land, SatelliteCheck, SatelliteCheckStatus

NO_GEOMETRY_BN = "এই জমির সীমানা আঁকা হয়নি। আগে মানচিত্রে প্লটের সীমানা আঁকুন।"
SERVICE_ERROR_BN = "স্যাটেলাইট সেবা থেকে ফল পাওয়া যায়নি"


class SatelliteServiceError(Exception):
    pass


def request_analysis(geometry: dict, buffer_m: float, years: list[int] | None) -> dict:
    payload: dict = {"geometry": geometry, "buffer_m": buffer_m}
    if years:
        payload["years"] = years
    try:
        resp = httpx.post(
            f"{settings.sentinel_url.rstrip('/')}/api/analyze-area",
            json=payload,
            timeout=settings.sentinel_timeout_s,
        )
    except httpx.HTTPError as error:
        raise SatelliteServiceError(f"{type(error).__name__}: {error}") from error
    try:
        body = resp.json()
    except ValueError:
        body = {}
    if resp.status_code != 200 or not body.get("success"):
        detail = body.get("message") or body.get("error") or resp.text[:200]
        raise SatelliteServiceError(f"HTTP {resp.status_code}: {detail}")
    return body["result"]


def start_check(
    db: Session, land: Land, buffer_m: float = 200.0, years: list[int] | None = None
) -> SatelliteCheck:
    check = SatelliteCheck(land_id=land.id, buffer_m=buffer_m, years=years)
    db.add(check)
    db.flush()
    return check


def run_check(
    db: Session,
    check_id: uuid.UUID,
    post: Callable[[dict, float, list[int] | None], dict] = request_analysis,
) -> SatelliteCheck | None:
    check = db.get(SatelliteCheck, check_id)
    if check is None or check.status != SatelliteCheckStatus.pending:
        return check  # deleted, or already finished (a redelivered task)
    land = db.get(Land, check.land_id)
    if land is None or not land.geometry:
        check.status, check.error = SatelliteCheckStatus.failed, NO_GEOMETRY_BN
    else:
        try:
            check.result = post(land.geometry, check.buffer_m, check.years)
            check.status = SatelliteCheckStatus.ok
        except Exception as error:  # noqa: BLE001 - any failure must end the pending state
            check.status, check.error = SatelliteCheckStatus.failed, f"{SERVICE_ERROR_BN}: {error}"
    db.commit()
    return check


def latest_check(
    db: Session, land_id: uuid.UUID, status: str | None = None
) -> SatelliteCheck | None:
    query = select(SatelliteCheck).where(SatelliteCheck.land_id == land_id)
    if status:
        query = query.where(SatelliteCheck.status == status)
    return db.scalars(
        query.order_by(SatelliteCheck.created_at.desc(), SatelliteCheck.id.desc()).limit(1)
    ).first()
