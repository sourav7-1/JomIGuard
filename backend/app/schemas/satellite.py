"""Plot geometry (GeoJSON Polygon, [lon, lat]) and satellite check records."""

import math
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.services.normalize import to_bangla_digits
from app.services.rules.base import RuleResult

# Same box as the sentinel service (sentinel/services/area_analysis.py)
BD_LON = (88.0, 92.8)
BD_LAT = (20.5, 26.7)
MAX_PLOT_ACRES = 50.0
SQ_M_PER_ACRE = 4046.8564224
EARTH_RADIUS_M = 6371008.8


def _ring_area_m2(ring: list[list[float]]) -> float:
    """Shoelace on a local equirectangular projection; plenty for plots of a few hectares."""
    lat0 = math.radians(sum(p[1] for p in ring) / len(ring))
    xy = [
        (math.radians(lon) * EARTH_RADIUS_M * math.cos(lat0), math.radians(lat) * EARTH_RADIUS_M)
        for lon, lat, *_ in ring
    ]
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(xy, xy[1:], strict=False))) / 2


def polygon_area_m2(coordinates: list[list[list[float]]]) -> float:
    outer, *holes = coordinates
    return max(0.0, _ring_area_m2(outer) - sum(_ring_area_m2(h) for h in holes))


class PlotGeometry(BaseModel):
    """GeoJSON Polygon of the plot. First ring is the outline, any further rings are holes."""

    type: Literal["Polygon"]
    coordinates: list[list[list[float]]] = Field(min_length=1)

    @field_validator("coordinates")
    @classmethod
    def _rings(cls, rings: list[list[list[float]]]) -> list[list[list[float]]]:
        for ring in rings:
            if len(ring) < 4:
                raise ValueError("প্লটের সীমানায় অন্তত ৩টি বিন্দু দরকার।")
            if any(len(p) < 2 for p in ring):
                raise ValueError("প্রতিটি বিন্দুতে দ্রাঘিমা ও অক্ষাংশ দরকার।")
            if ring[0][:2] != ring[-1][:2]:
                raise ValueError("প্লটের সীমানা বন্ধ নয়: প্রথম ও শেষ বিন্দু এক হতে হবে।")
            for lon, lat, *_ in ring:
                if not (BD_LON[0] <= lon <= BD_LON[1] and BD_LAT[0] <= lat <= BD_LAT[1]):
                    raise ValueError("প্লটটি বাংলাদেশের ভেতরে হতে হবে।")
        return rings

    @model_validator(mode="after")
    def _area(self) -> "PlotGeometry":
        area = polygon_area_m2(self.coordinates)
        if area <= 0:
            raise ValueError("প্লটের ক্ষেত্রফল শূন্য।")
        if area > MAX_PLOT_ACRES * SQ_M_PER_ACRE:
            acres = to_bangla_digits(f"{MAX_PLOT_ACRES:.0f}")
            raise ValueError(f"প্লট {acres} একরের বেশি বড় হতে পারবে না।")
        return self


class SatelliteCheckIn(BaseModel):
    buffer_m: float = Field(200.0, ge=0, le=1000)
    years: list[int] | None = None  # None = service default (2019..2025)


class SatelliteCheckOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    land_id: uuid.UUID
    created_at: datetime
    status: Literal["pending", "ok", "failed"]
    buffer_m: float
    years: list[int] | None
    result: dict | None
    error: str | None


class SatelliteCheckView(SatelliteCheckOut):
    """Latest check plus its findings (services/satellite_findings.py) for the results card."""

    findings: list[RuleResult] = Field(default_factory=list)
    group_title_bn: str = "স্যাটেলাইট যাচাই"
    area_note_bn: str | None = None
