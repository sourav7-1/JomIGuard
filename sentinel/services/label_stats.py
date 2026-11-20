"""Area statistics and border-uncertainty analysis for saved labels.

Computed automatically on every "Save labels":

* Total selected area (m2): geodesic area of the AOI polygon, plus the
  area actually covered by each image grid (they differ slightly because a
  raster can only follow the polygon edge pixel by pixel).
* Area and share of each labeled class, plus the unlabeled rest ("Other":
  buildings, roads, water, bare soil, ... -- everything not labeled).
* Border analysis. Annotators draw conservatively (only where they are
  sure, e.g. tree canopy), so the true area of a class is usually a little
  larger than what was drawn. For every labeled class we look at a narrow
  band just OUTSIDE its polygons, over unlabeled pixels only:
    - certain   = what was drawn (lower bound)
    - estimated = certain + the band pixels that actually look like that
                  kind of surface (vegetation test for tree/grass/shrub:
                  Excess Green on the screenshot, NDVI on the GeoTIFF; for
                  other classes half the band is used)
    - maximum   = certain + the whole band (upper bound)
  The estimate therefore only grows where the image itself supports it,
  and never by more than the band width.

Pixel areas are exact per row: Web Mercator pixels shrink with latitude
(screenshot), and 10 m-in-degrees pixels are narrower east-west away from
the equator (GeoTIFF).
"""

from __future__ import annotations

import csv
import io
import math
from typing import Any, Optional

import numpy as np

from services import labeling_service as L

EARTH_RADIUS_M = 6371008.8
DEFAULT_BORDER_BAND_M = 2.0
MAX_BORDER_BAND_M = 20.0
VEGETATION_KEYS = {"forest_tree", "grass_crop", "shrub"}
EXG_THRESHOLD = 0.08   # Excess Green (2g - r - b, chromatic coords): > 0.08 = green vegetation
NDVI_THRESHOLD = 0.35  # GeoTIFF NDVI band: > 0.35 = vegetation
OTHER_CLASS_ID = 9     # "Unknown" -- used for the unlabeled rest when filling


# ---------------------------------------------------------------------------
# Areas
# ---------------------------------------------------------------------------

def geodesic_area_m2(ring: list) -> float:
    """Area of a lon/lat ring on the sphere (error well under 0.5% for the
    small areas used here)."""
    ring = L.close_polygon_ring(ring)
    total = 0.0
    for (lon1, lat1), (lon2, lat2) in zip(ring, ring[1:]):
        total += math.radians(lon2 - lon1) * (2 + math.sin(math.radians(lat1)) + math.sin(math.radians(lat2)))
    return abs(total) * EARTH_RADIUS_M ** 2 / 2


def screenshot_pixel_areas(reference_info: dict[str, Any]) -> np.ndarray:
    """(H, 1) ground area in m2 of one screenshot pixel, per row."""
    zoom = reference_info["zoom"]
    height = reference_info["height"]
    resolution = L._mercator_resolution_m(zoom)
    n = L.TILE_SIZE_PX * 2 ** zoom
    world_y = reference_info["origin_world_px_y"] + np.arange(height) + 0.5
    lat = np.arctan(np.sinh(np.pi * (1 - 2 * world_y / n)))
    return ((resolution * np.cos(lat)) ** 2)[:, None]


def geotiff_pixel_areas(transform, crs, height: int) -> np.ndarray:
    """(H, 1) ground area in m2 of one GeoTIFF pixel, per row."""
    if crs is not None and getattr(crs, "is_geographic", str(crs) == "EPSG:4326"):
        lat = transform.f + transform.e * (np.arange(height) + 0.5)
        dx = abs(transform.a) * 111320.0 * np.cos(np.radians(lat))
        dy = abs(transform.e) * 110574.0
        return (dx * dy)[:, None]
    return np.full((height, 1), abs(transform.a * transform.e))


# ---------------------------------------------------------------------------
# Morphology / surface tests (numpy only)
# ---------------------------------------------------------------------------

def _dilate_full(mask: np.ndarray, radius_px: int) -> np.ndarray:
    out = mask.copy()
    for step in range(radius_px):
        p = np.pad(out, 1)
        out = p[1:-1, 1:-1].copy()          # in place from here: ~2 arrays alive
        out |= p[:-2, 1:-1]
        out |= p[2:, 1:-1]
        out |= p[1:-1, :-2]
        out |= p[1:-1, 2:]
        if step % 2 == 1:
            out |= p[:-2, :-2]
            out |= p[:-2, 2:]
            out |= p[2:, :-2]
            out |= p[2:, 2:]
        del p
    return out


def dilate(mask: np.ndarray, radius_px: int) -> np.ndarray:
    """Binary dilation by ~radius_px, alternating cross and square steps so
    the grown band is close to round (octagon) rather than a square. Works
    only inside the mask's bounding box (+ radius), so small classes on a
    large screenshot cost almost no memory."""
    radius_px = max(0, int(radius_px))
    if radius_px == 0 or not mask.any():
        return mask.copy()
    rows = np.flatnonzero(mask.any(axis=1))
    cols = np.flatnonzero(mask.any(axis=0))
    r0, r1 = max(0, rows[0] - radius_px), min(mask.shape[0], rows[-1] + radius_px + 1)
    c0, c1 = max(0, cols[0] - radius_px), min(mask.shape[1], cols[-1] + radius_px + 1)
    out = np.zeros_like(mask)
    out[r0:r1, c0:c1] = _dilate_full(mask[r0:r1, c0:c1], radius_px)
    return out


def greenness(rgb: np.ndarray, rows_per_chunk: int = 256) -> np.ndarray:
    """Excess Green index on chromatic coordinates -> True = vegetation.
    (2g - r - b > T with r,g,b = R,G,B / (R+G+B)) is evaluated in integer
    form, a few hundred rows at a time, so a 4096 x 4096 screenshot needs
    only a few MB of working memory (the free server has 512 MB)."""
    out = np.zeros(rgb.shape[:2], dtype=bool)
    scale = 1000
    threshold = int(round(EXG_THRESHOLD * scale))
    for start in range(0, rgb.shape[0], rows_per_chunk):
        block = rgb[start:start + rows_per_chunk, :, :3].astype(np.int32)
        r, g, b = block[..., 0], block[..., 1], block[..., 2]
        out[start:start + rows_per_chunk] = scale * (2 * g - r - b) > threshold * (r + g + b)
    return out


# ---------------------------------------------------------------------------
# Statistics on one grid
# ---------------------------------------------------------------------------

def _grid_stats(mask: np.ndarray, allowed: np.ndarray, pixel_area: np.ndarray, band_px: int,
                vegetation: Optional[np.ndarray], grid_name: str, pixel_size_m: float) -> tuple[dict, np.ndarray]:
    row_area = np.asarray(pixel_area, dtype=np.float64).reshape(-1)
    labeled = (mask != L.IGNORE_LABEL_VALUE) & allowed

    def m2(selection):
        # per-row pixel counts x per-row pixel area: no large temporaries
        return float(np.count_nonzero(selection, axis=1) @ row_area)

    total_m2 = m2(allowed)

    def pct(value):
        return round(100.0 * value / total_m2, 3) if total_m2 else 0.0

    any_band = (dilate(labeled, band_px) & allowed & ~labeled) if band_px > 0 else np.zeros_like(labeled)

    classes = []
    for class_id in sorted(int(c) for c in np.unique(mask[labeled])):
        entry = L._CLASS_BY_ID.get(class_id, {"key": str(class_id), "label": str(class_id), "color": "#ffffff"})
        selection = (mask == class_id) & allowed
        certain = m2(selection)
        row = {
            "class_id": class_id,
            "class_key": entry["key"],
            "class_name": entry["label"],
            "color": entry["color"],
            "pixels": int(selection.sum()),
            "area_m2": round(certain, 2),
            "percent": pct(certain),
        }
        if band_px > 0:
            band = dilate(selection, band_px) & allowed & ~labeled
            band_m2 = m2(band)
            if vegetation is not None and entry["key"] in VEGETATION_KEYS:
                supported = m2(band & vegetation)
                method = "vegetation pixels in the border band"
            else:
                supported = band_m2 / 2
                method = "half of the border band"
            estimated = certain + supported
            maximum = certain + band_m2
            row["border"] = {
                "band_area_m2": round(band_m2, 2),
                "supported_area_m2": round(supported, 2),
                "method": method,
                "certain_m2": round(certain, 2),
                "estimated_m2": round(estimated, 2),
                "maximum_m2": round(maximum, 2),
                "certain_percent": pct(certain),
                "estimated_percent": pct(estimated),
                "maximum_percent": pct(maximum),
                # half-width of the [certain, maximum] range, relative to the estimate
                "uncertainty_percent": round(100.0 * (maximum - certain) / 2 / estimated, 1) if estimated else 0.0,
            }
        classes.append(row)

    labeled_m2 = m2(labeled)
    band_m2 = m2(any_band)
    other_m2 = total_m2 - labeled_m2 - band_m2
    return {
        "grid": grid_name,
        "pixel_size_m": round(pixel_size_m, 3),
        "border_band_px": int(band_px),
        "area_m2": round(total_m2, 2),
        "classes": classes,
        "labeled": {"area_m2": round(labeled_m2, 2), "percent": pct(labeled_m2)},
        "uncertain_border": {"area_m2": round(band_m2, 2), "percent": pct(band_m2)},
        "other_unlabeled": {"area_m2": round(other_m2, 2), "percent": pct(other_m2)},
    }, any_band


def compute(
    coordinates: list,
    border_band_m: float,
    screenshot: Optional[dict] = None,  # {"mask", "aoi", "rgb", "reference_info"}
    geotiff: Optional[dict] = None,     # {"mask", "allowed", "stack", "transform", "crs"}
) -> tuple[dict[str, Any], Optional[np.ndarray], Optional[np.ndarray]]:
    """Returns (stats, screenshot_border_band, geotiff_border_band)."""
    border_band_m = max(0.0, min(float(border_band_m), MAX_BORDER_BAND_M))
    stats: dict[str, Any] = {
        "aoi_area_m2": round(geodesic_area_m2(coordinates), 2),
        "border_band_m": border_band_m,
        "unlabeled_meaning": "Everything not labeled inside the selected area (buildings, roads, water, bare soil, ...) = Other.",
    }
    stats["aoi_area_ha"] = round(stats["aoi_area_m2"] / 10000, 4)
    ss_band = tif_band = None

    if screenshot is not None:
        info = screenshot["reference_info"]
        ground = info.get("ground_resolution_m") or math.sqrt(float(screenshot_pixel_areas(info).mean()))
        band_px = int(math.ceil(border_band_m / ground)) if border_band_m > 0 else 0
        stats["screenshot_grid"], ss_band = _grid_stats(
            screenshot["mask"], screenshot["aoi"], screenshot_pixel_areas(info), band_px,
            greenness(screenshot["rgb"]), "screenshot", ground,
        )

    if geotiff is not None:
        transform, crs = geotiff["transform"], geotiff["crs"]
        stack = geotiff["stack"]
        ndvi = np.nan_to_num(stack[3], nan=-1.0, posinf=-1.0, neginf=-1.0) if stack.shape[0] > 3 else None
        pixel_area = geotiff_pixel_areas(transform, crs, geotiff["mask"].shape[0])
        # At 10 m the uncertain border is the ring of mixed pixels around a class.
        band_px = 1 if border_band_m > 0 else 0
        stats["geotiff_grid"], tif_band = _grid_stats(
            geotiff["mask"], geotiff["allowed"], pixel_area, band_px,
            (ndvi > NDVI_THRESHOLD) if ndvi is not None else None, "geotiff",
            math.sqrt(float(pixel_area.mean())),
        )

    stats["primary_grid"] = "screenshot" if "screenshot_grid" in stats else ("geotiff" if "geotiff_grid" in stats else None)
    return stats, ss_band, tif_band


def fill_unlabeled_as_other(mask: np.ndarray, allowed: np.ndarray, border_band: Optional[np.ndarray]) -> np.ndarray:
    """Unlabeled pixels inside the area become OTHER_CLASS_ID, except the
    uncertain border band, which stays 255 (ignore) so a model is never
    trained on a guessed edge."""
    filled = mask.copy()
    target = allowed & (mask == L.IGNORE_LABEL_VALUE)
    if border_band is not None:
        target &= ~border_band
    filled[target] = OTHER_CLASS_ID
    return filled


def to_csv(stats: dict[str, Any]) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["grid", "item", "area_m2", "percent_of_area", "certain_m2", "estimated_m2", "maximum_m2",
                     "estimated_percent", "maximum_percent", "uncertainty_percent"])
    writer.writerow(["polygon (geodesic)", "selected area", stats["aoi_area_m2"], 100, "", "", "", "", "", ""])
    for key in ("screenshot_grid", "geotiff_grid"):
        grid = stats.get(key)
        if not grid:
            continue
        name = grid["grid"]
        writer.writerow([name, "selected area (on this grid)", grid["area_m2"], 100, "", "", "", "", "", ""])
        for row in grid["classes"]:
            border = row.get("border") or {}
            writer.writerow([name, row["class_name"], row["area_m2"], row["percent"],
                             border.get("certain_m2", ""), border.get("estimated_m2", ""), border.get("maximum_m2", ""),
                             border.get("estimated_percent", ""), border.get("maximum_percent", ""),
                             border.get("uncertainty_percent", "")])
        writer.writerow([name, "uncertain border (ignored)", grid["uncertain_border"]["area_m2"], grid["uncertain_border"]["percent"], "", "", "", "", "", ""])
        writer.writerow([name, "other / not labeled", grid["other_unlabeled"]["area_m2"], grid["other_unlabeled"]["percent"], "", "", "", "", "", ""])
    return out.getvalue()
