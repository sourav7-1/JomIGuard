"""Sentinel-1/2 helpers (Google Earth Engine) used by the collection service.
Trimmed copy of the original earth_engine_service.py: only the functions the
10-band collection actually calls."""
from datetime import datetime, timedelta

from pathlib import Path

import os

import ee

# Load .env (if present) so EARTH_ENGINE_PROJECT_ID can be set per machine.
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

PROJECT_ID = os.environ.get("EARTH_ENGINE_PROJECT_ID", "inner-strategy-495709-q2")

FINAL_BAND_ORDER = [
    "B4",
    "B3",
    "B2",
    "NDVI",
    "EVI",
    "NBR",
    "VV",
    "VH",
    "VV_VH_ratio",
    "VV_minus_VH"
]

def initialize_earth_engine():
    try:
        ee.Initialize(project=PROJECT_ID)
        print(f"Earth Engine Connected Successfully! (project: {PROJECT_ID})")

    except Exception as error:
        print(
            f"Earth Engine connection failed for project '{PROJECT_ID}': {error}\n"
            "If this project ID is not yours: copy .env.example to .env and set "
            "EARTH_ENGINE_PROJECT_ID to your own registered Earth Engine project "
            "(https://code.earthengine.google.com), then also run "
            "'earthengine authenticate' once from this terminal if you haven't."
        )
        raise

def validate_coordinates(coordinates):
    if not coordinates:
        raise ValueError("Coordinates পাওয়া যায়নি।")

    if not isinstance(coordinates, list):
        raise ValueError("Coordinates অবশ্যই list হতে হবে।")

    if len(coordinates) < 3:
        raise ValueError(
            "Polygon তৈরির জন্য কমপক্ষে ৩টি point প্রয়োজন।"
        )

    for point in coordinates:
        if not isinstance(point, list) or len(point) != 2:
            raise ValueError(
                "প্রতিটি coordinate "
                "[longitude, latitude] format-এ হতে হবে।"
            )

        longitude, latitude = point

        if not isinstance(longitude, (int, float)):
            raise ValueError(
                "Longitude অবশ্যই number হতে হবে।"
            )

        if not isinstance(latitude, (int, float)):
            raise ValueError(
                "Latitude অবশ্যই number হতে হবে।"
            )

        if longitude < -180 or longitude > 180:
            raise ValueError(
                "Longitude -180 থেকে 180-এর মধ্যে হতে হবে।"
            )

        if latitude < -90 or latitude > 90:
            raise ValueError(
                "Latitude -90 থেকে 90-এর মধ্যে হতে হবে।"
            )

def close_polygon(coordinates):
    polygon_coordinates = [
        point.copy()
        for point in coordinates
    ]

    if polygon_coordinates[0] != polygon_coordinates[-1]:
        polygon_coordinates.append(
            polygon_coordinates[0].copy()
        )

    return polygon_coordinates

def mask_sentinel2(image):
    """
    SCL classification ব্যবহার করে cloud, shadow,
    cirrus এবং snow pixel বাদ দেয়।

    Class 7 (unclassified) is also excluded: Sentinel-2's Scene
    Classification Layer routinely dumps ambiguous cloud-edge and
    thin-haze pixels into this bucket rather than the cloud classes,
    so puffy white artifacts can otherwise slip through masking even
    though the scene-level cloud filter passed. SCL is still not a
    perfect cloud detector, so some residual cloud can remain even
    with this widened mask.
    """

    scl = image.select("SCL")

    mask = (
        scl.neq(3)
        .And(scl.neq(7))
        .And(scl.neq(8))
        .And(scl.neq(9))
        .And(scl.neq(10))
        .And(scl.neq(11))
    )

    return (
        image
        .updateMask(mask)
        .select(["B2", "B3", "B4", "B8", "B12"])
    )

def get_collection_acquisition_metadata(collection):
    sorted_collection = collection.sort(
        "system:time_start"
    )

    acquisition_dates = ee.List(
        sorted_collection.aggregate_array(
            "system:time_start"
        )
    ).map(
        lambda timestamp: ee.Date(timestamp).format(
            "YYYY-MM-dd"
        )
    )

    metadata = ee.Dictionary({
        "image_count": sorted_collection.size(),
        "acquisition_dates": acquisition_dates
    }).getInfo()

    return (
        int(metadata.get("image_count", 0)),
        metadata.get("acquisition_dates", [])
    )

def compute_quality_flag(
    s2_count,
    s1_count,
    average_cloud,
    missing_percentage
):
    s2_count = int(s2_count or 0)
    s1_count = int(s1_count or 0)

    try:
        average_cloud = float(average_cloud)
    except (TypeError, ValueError):
        average_cloud = 100

    try:
        missing_percentage = float(
            missing_percentage
        )
    except (TypeError, ValueError):
        missing_percentage = 100

    if s2_count == 0 or s1_count == 0:
        return "WEAK"

    if (
        s2_count >= 3 and
        s1_count >= 3 and
        average_cloud <= 20 and
        missing_percentage <= 10
    ):
        return "GOOD"

    if (
        average_cloud <= 50 and
        missing_percentage <= 35
    ):
        return "FAIR"

    return "WEAK"

def get_period_quality_metrics(
    sentinel2_collection,
    sentinel2_composite,
    selected_area
):
    pixel_area = ee.Image.pixelArea()
    valid_mask = (
        sentinel2_composite
        .select("B4")
        .mask()
        .unmask(0)
    )

    area_statistics = ee.Dictionary(
        pixel_area
        .rename("total_area")
        .addBands(
            pixel_area
            .multiply(valid_mask)
            .rename("valid_area")
        )
        .reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=selected_area,
            scale=10,
            maxPixels=1e13,
            bestEffort=True
        )
    )

    total_area = ee.Number(
        area_statistics.get("total_area", 0)
    )
    valid_area = ee.Number(
        area_statistics.get("valid_area", 0)
    )

    missing_percentage = ee.Number(
        ee.Algorithms.If(
            total_area.gt(0),
            ee.Number(100).subtract(
                valid_area
                .divide(total_area)
                .multiply(100)
            ),
            100
        )
    ).max(0).min(100)

    metrics = ee.Dictionary({
        "average_cloud": sentinel2_collection.aggregate_mean(
            "CLOUDY_PIXEL_PERCENTAGE"
        ),
        "best_cloud": sentinel2_collection.aggregate_min(
            "CLOUDY_PIXEL_PERCENTAGE"
        ),
        "worst_cloud": sentinel2_collection.aggregate_max(
            "CLOUDY_PIXEL_PERCENTAGE"
        ),
        "missing_percentage": missing_percentage
    }).getInfo()

    def get_metric(name, fallback=0):
        try:
            return round(
                float(metrics.get(name, fallback)),
                2
            )
        except (TypeError, ValueError):
            return float(fallback)

    return {
        "average_cloud": get_metric(
            "average_cloud", 100
        ),
        "best_cloud": get_metric(
            "best_cloud", 100
        ),
        "worst_cloud": get_metric(
            "worst_cloud", 100
        ),
        "missing_percentage": get_metric(
            "missing_percentage", 100
        )
    }

def build_quality_warnings(
    period_label,
    s2_count,
    s1_count,
    quality_metrics,
    quality_flag
):
    warnings = []

    if int(s2_count) < 3:
        warnings.append(
            f"{period_label} has fewer than 3 "
            "Sentinel-2 scenes."
        )

    if int(s1_count) < 3:
        warnings.append(
            f"{period_label} has fewer than 3 "
            "Sentinel-1 scenes."
        )

    if quality_metrics["average_cloud"] > 20:
        warnings.append(
            f"{period_label} average scene cloud is "
            f"{quality_metrics['average_cloud']:.2f}%."
        )

    if quality_metrics["missing_percentage"] > 10:
        warnings.append(
            f"{period_label} optical composite has "
            f"{quality_metrics['missing_percentage']:.2f}% "
            "missing coverage."
        )

    if quality_flag == "WEAK":
        warnings.append(
            f"{period_label} quality is WEAK. Widen the "
            "date range or adjust the cloud threshold "
            "before downstream comparison."
        )

    return warnings
