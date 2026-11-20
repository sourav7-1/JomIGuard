import pytest
from conftest import TestSession
from pydantic import ValidationError
from sqlalchemy import select

from app.models import Land, SatelliteCheck, SatelliteCheckStatus
from app.schemas.land_case import LandOut
from app.schemas.satellite import (
    SQ_M_PER_ACRE,
    PlotGeometry,
    SatelliteCheckIn,
    SatelliteCheckOut,
    polygon_area_m2,
)

# ~205 m x 222 m near Gazipur (synthetic test plot, ~11 acres)
RING = [[90.41, 23.99], [90.412, 23.99], [90.412, 23.992], [90.41, 23.992], [90.41, 23.99]]


def square(lon, lat, side_deg):
    return [
        [lon, lat],
        [lon + side_deg, lat],
        [lon + side_deg, lat + side_deg],
        [lon, lat + side_deg],
        [lon, lat],
    ]


def test_valid_polygon_and_area():
    geo = PlotGeometry(type="Polygon", coordinates=[RING])
    acres = polygon_area_m2(geo.coordinates) / SQ_M_PER_ACRE
    assert 10 < acres < 12


def test_area_of_100m_square_is_about_one_hectare():
    side = 100 / 111_195  # degrees of latitude per 100 m
    lat_side = side
    lon_side = side / 0.9135  # cos(24°)
    ring = [
        [90.0, 24.0],
        [90.0 + lon_side, 24.0],
        [90.0 + lon_side, 24.0 + lat_side],
        [90.0, 24.0 + lat_side],
        [90.0, 24.0],
    ]
    assert polygon_area_m2([ring]) == pytest.approx(10_000, rel=0.01)


def test_hole_reduces_area():
    outer = square(90.41, 23.99, 0.002)
    hole = square(90.4105, 23.9905, 0.001)
    assert polygon_area_m2([outer, hole]) == pytest.approx(
        polygon_area_m2([outer]) * 0.75, rel=0.01
    )


@pytest.mark.parametrize(
    "geometry, message",
    [
        ({"type": "Point", "coordinates": [90.41, 23.99]}, None),
        ({"type": "Polygon", "coordinates": [RING[:-1]]}, "বন্ধ নয়"),
        ({"type": "Polygon", "coordinates": [RING[:3]]}, "অন্তত ৩টি"),
        ({"type": "Polygon", "coordinates": [square(77.2, 28.6, 0.001)]}, "বাংলাদেশের ভেতরে"),
        ({"type": "Polygon", "coordinates": [square(90.4, 23.9, 0.02)]}, "৫০ একরের"),
        ({"type": "Polygon", "coordinates": [[[90.41, 23.99]] * 4]}, "শূন্য"),
    ],
)
def test_invalid_geometry_rejected(geometry, message):
    with pytest.raises(ValidationError) as err:
        PlotGeometry.model_validate(geometry)
    if message:
        assert message in str(err.value)


def test_check_in_limits():
    assert SatelliteCheckIn().buffer_m == 200
    with pytest.raises(ValidationError):
        SatelliteCheckIn(buffer_m=5000)


def test_land_geometry_and_check_roundtrip_and_cascade():
    with TestSession.begin() as db:
        land = Land(
            district="গাজীপুর",
            upazila="সদর",
            mouza="ডেমো",
            dag_no="305/1",
            khatian_no="১২",
            geometry={"type": "Polygon", "coordinates": [RING]},
        )
        db.add(land)
        db.flush()
        check = SatelliteCheck(land_id=land.id, years=[2019, 2025])
        db.add(check)
        db.flush()
        land_id, check_id = land.id, check.id

    with TestSession() as db:
        land = db.get(Land, land_id)
        assert LandOut.model_validate(land).geometry["coordinates"] == [RING]
        out = SatelliteCheckOut.model_validate(db.get(SatelliteCheck, check_id))
        assert out.status == SatelliteCheckStatus.pending
        assert out.buffer_m == 200 and out.years == [2019, 2025] and out.result is None

    with TestSession.begin() as db:
        db.delete(db.get(Land, land_id))
    with TestSession() as db:
        assert db.scalar(select(SatelliteCheck).where(SatelliteCheck.id == check_id)) is None


def test_land_without_geometry_is_null():
    with TestSession.begin() as db:
        land = Land(district="ঢাকা", upazila="সদর", mouza="ডেমো", dag_no="১", khatian_no="২")
        db.add(land)
    assert LandOut.model_validate(land).geometry is None
