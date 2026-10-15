import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Land
from app.schemas.land_case import LandCase, LandIn, LandOut
from app.services.land_case import load_land_case

router = APIRouter(prefix="/lands", tags=["lands"])

Db = Annotated[Session, Depends(get_db)]


@router.post("", response_model=LandOut, status_code=201)
def create_land(body: LandIn, db: Db):
    # ponytail: lands columns are NOT NULL; "" for an unknown district/upazila/khatian until a
    # migration makes them nullable
    land = Land(
        district=body.district or "",
        upazila=body.upazila or "",
        mouza=body.mouza,
        dag_no=body.dag_no,
        khatian_no=body.khatian_no or "",
    )
    db.add(land)
    db.commit()
    return land


@router.get("/{land_id}/case", response_model=LandCase)
def get_land_case(land_id: uuid.UUID, db: Db):
    """The land case as the rule engine will see it (debug view until the case page)."""
    if db.get(Land, land_id) is None:
        raise HTTPException(404, "Land not found")
    return load_land_case(db, land_id)
