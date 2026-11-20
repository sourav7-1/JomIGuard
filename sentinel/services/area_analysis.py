"""Multi-year satellite check for one land plot (used by JomiGuard).

Input: the plot polygon (GeoJSON, lon/lat). The polygon is buffered
(default 200 m) because a small plot is only a few 10 m Sentinel pixels,
so the result describes the plot's surroundings, not the plot alone.

For every requested year a February 10-band Sentinel-1/2 composite is
built and downloaded. Two kinds of numbers come out of it:

* indices (used for trends): NDVI statistics, a water fraction from
  NDVI + Sentinel-1 VV backscatter, and the Gazipur-calibrated tree-cover
  regression (CV R² 0.94). These are physical measurements or a
  well-validated model, so they are stable from one year to the next.
* U-Net land-cover map (one year at a time only): water, tree,
  grass/crop and building (validation IoU 0.82 / 0.69 / 0.52 / 0.81).
  The U-Net is NOT used for trends: at 74 % pixel accuracy, small changes
  in a year's image can flip whole areas between classes, so differencing
  two yearly maps produces fake "changes".
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Any

import ee
import numpy as np

from services import historical_collection_service as hist

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ai"))
import core as ai  # noqa: E402

REPORTED = {0: "water", 1: "tree", 2: "grass_crop", 5: "building"}
MIN_YEAR, MAX_YEAR = 2019, 2025  # Sentinel-2 SR coverage of Bangladesh is reliable from 2019
DEFAULT_YEARS = list(range(MIN_YEAR, MAX_YEAR + 1))
MAX_BUFFER_M = 1000
MAX_AREA_KM2 = 5.0


def _outer_ring(geometry: dict[str, Any]) -> list:
    if not isinstance(geometry, dict):
        raise ValueError("geometry must be a GeoJSON object.")
    if geometry.get("type") == "Feature":
        geometry = geometry.get("geometry") or {}
    if geometry.get("type") != "Polygon" or not geometry.get("coordinates"):
        raise ValueError("geometry must be a GeoJSON Polygon.")
    ring = geometry["coordinates"][0]
    if len(ring) < 3:
        raise ValueError("Polygon needs at least 3 points.")
    for lon, lat, *_ in ring:
        if not (88.0 <= lon <= 92.8 and 20.5 <= lat <= 26.7):
            raise ValueError("Polygon must be inside Bangladesh.")
    return [[float(p[0]), float(p[1])] for p in ring]


def _clean_years(years) -> list[int]:
    years = sorted({int(y) for y in (years or DEFAULT_YEARS)})
    bad = [y for y in years if y < MIN_YEAR or y > MAX_YEAR]
    if bad or not years:
        raise ValueError(f"years must be between {MIN_YEAR} and {MAX_YEAR}.")
    return years[:7]


# Band positions in the 10-band stack (see ai/core.py BAND_NAMES)
NDVI_IDX, VV_IDX = 3, 6
WATER_NDVI_MAX = 0.0       # open water has NDVI below 0
WET_VV_DB_MAX = -17.0      # calm water is dark in Sentinel-1 VV (dB) ...
WET_NDVI_MAX = 0.2         # ... and not green
DENSE_GREEN_NDVI = 0.5


def _indices(tif: Path) -> dict[str, Any]:
    """Physical indices over valid pixels; stable across years."""
    bands, valid = ai.read_stack(tif)
    n = int(valid.sum())
    if n == 0:
        raise ValueError("No valid pixels in this year's image.")
    ndvi = bands[NDVI_IDX][valid]
    vv = bands[VV_IDX][valid]
    water = (ndvi < WATER_NDVI_MAX) | ((vv < WET_VV_DB_MAX) & (ndvi < WET_NDVI_MAX))
    return {
        "ndvi_mean": round(float(np.mean(ndvi)), 3),
        "ndvi_median": round(float(np.median(ndvi)), 3),
        "dense_green_pct": round(100 * float(np.mean(ndvi >= DENSE_GREEN_NDVI)), 2),
        "water_pct": round(100 * float(np.mean(water)), 2),
        "valid_pixels": n,
    }


def _map_classes(analysis: dict) -> dict[str, float]:
    pct = {name: 0.0 for name in REPORTED.values()}
    for c in analysis["classes"]:
        if c["id"] in REPORTED:
            pct[REPORTED[c["id"]]] = c["percent"]
    pct["other"] = round(max(0.0, 100.0 - sum(pct.values())), 2)
    return pct


TREND_KEYS = ("tree_cover_pct", "water_pct", "dense_green_pct", "ndvi_mean")


# A change counts as persistent only if it is at least this big (metric units)
PERSIST_THRESHOLD = {"tree_cover_pct": 10.0, "dense_green_pct": 10.0, "water_pct": 5.0, "ndvi_mean": 0.05}
OUTLIER_MADS = 3.0
WATER_SPIKE_MIN_POINTS = 5.0
WATER_HEAVY_PCT = 20.0
MIN_S2_DATES = 2


def _scene_info(comp: dict) -> dict[str, Any]:
    """Each date is usually 2 tiles over the plot; dedupe dates, keep tile counts."""
    s2 = sorted(set(comp.get("sentinel2_dates") or []))
    s1 = sorted(set(comp.get("sentinel1_dates") or []))
    return {"sentinel2_tile_count": comp.get("sentinel2_scene_count"),
            "sentinel1_tile_count": comp.get("sentinel1_scene_count"),
            "sentinel2_dates": s2, "sentinel1_dates": s1,
            "sentinel2_unique_dates": len(s2)}


def _low_confidence(rec: dict) -> bool:
    return rec.get("sentinel2_unique_dates", 0) < MIN_S2_DATES or rec.get("quality_flag") != "GOOD"


def _theil_sen(years: np.ndarray, values: np.ndarray) -> float:
    i, j = np.triu_indices(len(years), k=1)
    return float(np.median((values[j] - values[i]) / (years[j] - years[i])))


def _outliers(years: list[int], values: np.ndarray, sides=(1, -1)) -> list[int]:
    """One-off years: more than 3 MAD from the median AND not part of a run.

    Two neighbouring years off on the same side are a real step change, not
    a bad image, so they are kept (plain MAD would flag a lasting drop that
    covers under half the years as "outliers" and hide it). `sides` limits
    which direction counts (water keeps its high years: they may be floods).
    """
    dev = values - np.median(values)
    mad = float(np.median(np.abs(dev)))
    if mad == 0:
        return []
    side = np.sign(dev)
    flagged = (np.abs(dev) > OUTLIER_MADS * mad) & np.isin(side, sides)
    out = []
    for k in np.flatnonzero(flagged):
        run = any(0 <= n < len(values) and flagged[n] and side[n] == side[k] for n in (k - 1, k + 1))
        if not run:
            out.append(years[k])
    return out


def _trend(per_year: list[dict], key: str) -> dict[str, Any] | None:
    ok = [y for y in per_year if y.get("status") == "ok" and y["metrics"].get(key) is not None]
    if len(ok) < 2:
        return None
    series = [{"year": y["year"], "value": y["metrics"][key], "low_confidence": bool(y.get("low_confidence"))}
              for y in ok]
    conf = [y for y in ok if not y.get("low_confidence")]
    result: dict[str, Any] = {
        "from_year": None, "to_year": None, "from": None, "to": None, "change": None,
        "slope_per_year": None, "outlier_years": [], "persistent_change": False,
        "low_confidence_years": [y["year"] for y in ok if y.get("low_confidence")],
        "series": series}
    if len(conf) < 2:
        return result
    years = [y["year"] for y in conf]
    values = np.array([float(y["metrics"][key]) for y in conf])
    # water: only low outliers are dropped; high ones may be real floods (see _signals)
    outlier_years = _outliers(years, values, sides=(-1,) if key == "water_pct" else (1, -1))
    clean = [(yr, v) for yr, v in zip(years, values) if yr not in outlier_years]
    a = float(np.median([v for _, v in clean[:2]]))
    b = float(np.median([v for _, v in clean[-2:]]))
    change = b - a
    # needs 4 clean years so the "first two" and "last two" don't overlap
    persistent = len(clean) >= 4 and abs(change) > 0 and all(
        (v - a) * np.sign(change) >= PERSIST_THRESHOLD[key] for _, v in clean[-2:])
    result.update({"from_year": clean[0][0], "to_year": clean[-1][0],
                   "from": round(a, 3), "to": round(b, 3),
                   "change": round(change, 3) + 0.0,  # +0.0 turns -0.0 into 0.0
                   "slope_per_year": round(_theil_sen(np.array(years, float), values), 4),
                   "outlier_years": outlier_years, "persistent_change": bool(persistent)})
    return result


def _signals(per_year: list[dict], trends: dict) -> dict[str, Any]:
    """Water signals use ALL ok years (outliers and low-confidence too) so a real flood is never dropped."""
    ok = [y for y in per_year if y.get("status") == "ok"]
    water = np.array([float(y["metrics"]["water_pct"]) for y in ok])
    spikes = []
    if len(ok) >= 3:
        # a spike is a jump above the Theil-Sen trend line, so a year that just continues a
        # steady rise (river erosion) is not a spike; that rise is the water_pct trend instead
        years = np.array([y["year"] for y in ok], float)
        slope = _theil_sen(years, water)
        resid = water - (float(np.median(water - slope * years)) + slope * years)
        mad = float(np.median(np.abs(resid - np.median(resid))))
        # ... and above what its neighbours predict (mean of both sides; at the ends, the line
        # through the two nearest years), so an accelerating rise is not a spike in its last year
        n = len(water)
        local = [(water[k - 1] + water[k + 1]) / 2 if 0 < k < n - 1
                 else 2 * water[1] - water[2] if k == 0 else 2 * water[-2] - water[-3]
                 for k in range(n)]
        spikes = [y["year"] for y, r, w, e in zip(ok, resid, water, local)
                  if r > OUTLIER_MADS * mad and r >= WATER_SPIKE_MIN_POINTS
                  and w - e >= WATER_SPIKE_MIN_POINTS]
    return {
        "water_heavy_years": [y["year"] for y in ok if y["metrics"]["water_pct"] >= WATER_HEAVY_PCT],
        "water_spike_years": spikes,
        "outlier_years": sorted({yr for t in trends.values() if t for yr in t["outlier_years"]}),
        "low_confidence_years": [y["year"] for y in ok if y.get("low_confidence")],
        "years_checked": len(ok),
    }


def analyze_area(geometry: dict, years=None, buffer_m: float = 200) -> dict[str, Any]:
    ring = _outer_ring(geometry)
    years = _clean_years(years)
    buffer_m = float(buffer_m)
    if not 0 <= buffer_m <= MAX_BUFFER_M:
        raise ValueError(f"buffer_m must be 0..{MAX_BUFFER_M}.")

    plot = ee.Geometry.Polygon([ring])
    area = plot.buffer(buffer_m) if buffer_m else plot
    area_km2 = area.area(maxError=1).getInfo() / 1e6
    if area_km2 > MAX_AREA_KM2:
        raise ValueError(f"Analysed area is {area_km2:.1f} km²; limit is {MAX_AREA_KM2} km².")
    bounds = area.bounds(maxError=1).coordinates().getInfo()[0]

    per_year = []
    with tempfile.TemporaryDirectory() as tmp:
        for year in years:
            rec: dict[str, Any] = {"year": year}
            try:
                comp = hist.build_year_composite_with_retry(area, f"{year}-02-01", f"{year}-02-28")
                rec.update(_scene_info(comp))
                if comp["image"] is None:
                    rec.update(status="no_data", reason=comp.get("error"))
                else:
                    tif = Path(tmp) / f"area_{year}.tif"
                    hist.download_geotiff(comp["image"], bounds, tif)
                    analysis = ai.analyse(tif)
                    analysis.pop("_seg", None)
                    counts = analysis.get("counts") or {}
                    metrics = _indices(tif)
                    metrics["tree_cover_pct"] = counts.get("tree_cover_pct")
                    rec.update(status="ok", quality_flag=comp["quality_flag"],
                               usable_pixel_pct=comp["usable_pixel_percentage"],
                               area_ha=analysis["area_ha"],
                               metrics=metrics,
                               tree_estimate=counts.get("total_trees"),
                               map_classes_pct=_map_classes(analysis))
                    rec["low_confidence"] = _low_confidence(rec)
            except Exception as error:  # noqa: BLE001 - one bad year must not fail the whole check
                rec.update(status="failed", reason=str(error))
            per_year.append(rec)

    trends = {k: _trend(per_year, k) for k in TREND_KEYS}
    return {
        "scope": "surroundings",  # plot + buffer, not the plot alone
        "buffer_m": buffer_m,
        "analysed_area_km2": round(area_km2, 3),
        "season": "February (dry season) composite each year",
        "years": per_year,
        "trends": trends,
        "signals": _signals(per_year, trends),
        "notes": [
            "10 m pixels: results describe the area around the plot, not the plot boundary.",
            "Trends use NDVI, a water index (NDVI + Sentinel-1 VV) and the tree-cover model, not the land-cover map.",
            "map_classes_pct is a single-year land-cover map (74% pixel accuracy); do not compare it across years.",
            "February is the dry season: standing water in February is a stronger signal (waterlogging, "
            "erosion, a pond or low land) than a monsoon flood would be. This check does not see monsoon flooding.",
            "Low-confidence years (fewer than 2 Sentinel-2 dates or quality not GOOD) stay in series "
            "but are left out of slope, from/to/change and persistent_change.",
        ],
        "model": {"segmentation_val_pixel_accuracy": 0.739, "tree_cover_r2": 0.94},
    }
