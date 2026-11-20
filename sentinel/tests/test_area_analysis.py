"""Robust trend tests. ee, the model and the collection service are stubbed: no network."""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
for name in ("ee", "core", "services.historical_collection_service"):
    sys.modules.setdefault(name, types.ModuleType(name))

from services.area_analysis import (  # noqa: E402
    DEFAULT_YEARS, _low_confidence, _scene_info, _signals, _trend)


def _years(values, key="tree_cover_pct"):
    return [{"year": y, "status": "ok", "metrics": {key: v}} for y, v in zip(DEFAULT_YEARS, values)]


def test_default_years_cover_2019_to_2025():
    assert DEFAULT_YEARS == [2019, 2020, 2021, 2022, 2023, 2024, 2025]


def test_one_dip_year_is_outlier_not_persistent():
    t = _trend(_years([39, 40, 22, 41, 40, 39, 41]), "tree_cover_pct")
    assert t["outlier_years"] == [2021]
    assert t["persistent_change"] is False
    assert abs(t["change"]) < 2


def test_drop_that_stays_down_is_persistent():
    t = _trend(_years([40, 41, 39, 40, 20, 21, 20]), "tree_cover_pct")
    assert t["outlier_years"] == []
    assert t["persistent_change"] is True
    assert t["change"] < -10
    assert t["slope_per_year"] < 0


def test_flat_series_has_no_outliers():
    t = _trend(_years([0.4] * 7, "ndvi_mean"), "ndvi_mean")
    assert t["outlier_years"] == [] and t["persistent_change"] is False


def test_single_high_water_year_is_spike_and_heavy_not_dropped():
    per_year = _years([0.3, 0.2, 0.1, 25.0, 0.2, 0.3, 0.1], "water_pct")
    trends = {"water_pct": _trend(per_year, "water_pct")}
    assert 2022 not in trends["water_pct"]["outlier_years"]  # high water stays in the trend
    sig = _signals(per_year, trends)
    assert sig["water_spike_years"] == [2022]
    assert sig["water_heavy_years"] == [2022]


def test_spike_below_heavy_threshold_is_spike_only():
    per_year = _years([0.3, 0.2, 0.1, 8.0, 0.2, 0.3, 0.1], "water_pct")
    sig = _signals(per_year, {"water_pct": _trend(per_year, "water_pct")})
    assert sig["water_spike_years"] == [2022]
    assert sig["water_heavy_years"] == []


def test_single_date_year_is_low_confidence_and_left_out_of_slope():
    rec = {"quality_flag": "GOOD", **_scene_info({"sentinel2_dates": ["2022-02-15", "2022-02-15"]})}
    assert _low_confidence(rec) is True
    per_year = _years([10, 11, 12, 100, 14, 15, 16])
    per_year[3]["low_confidence"] = True
    t = _trend(per_year, "tree_cover_pct")
    assert t["slope_per_year"] == 1.0
    assert t["low_confidence_years"] == [2022]
    assert t["series"][3] == {"year": 2022, "value": 100, "low_confidence": True}


def test_fair_quality_is_low_confidence():
    assert _low_confidence({"quality_flag": "FAIR", "sentinel2_unique_dates": 5}) is True
    assert _low_confidence({"quality_flag": "GOOD", "sentinel2_unique_dates": 2}) is False


def test_duplicate_dates_counted_once():
    info = _scene_info({"sentinel2_scene_count": 4, "sentinel1_scene_count": 2,
                        "sentinel2_dates": ["2023-02-10", "2023-02-05", "2023-02-05", "2023-02-10"],
                        "sentinel1_dates": ["2023-02-07", "2023-02-07"]})
    assert info["sentinel2_dates"] == ["2023-02-05", "2023-02-10"]
    assert info["sentinel2_unique_dates"] == 2
    assert info["sentinel1_dates"] == ["2023-02-07"]
    assert info["sentinel2_tile_count"] == 4 and info["sentinel1_tile_count"] == 2
