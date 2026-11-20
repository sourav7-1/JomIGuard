"""Basemap screenshot capture, polygon labeling, and training-dataset output
for TWO independent models:

  * Approach 1 -- GeoTIFF model: input = the 10-band Sentinel-1/2 GeoTIFF,
    target = <stem>_mask.png / <stem>_mask.tif on the GeoTIFF's own grid.
  * Approach 2 -- Screenshot model: input = the high-resolution basemap
    screenshot, target = <stem>_screenshot_mask.png on the screenshot grid.

Both masks are generated from ONE canonical set of polygons stored in real
geographic coordinates (EPSG:4326 lon/lat, also saved as GeoJSON). Whatever
image the annotator drew on, every polygon is first converted to lon/lat,
then rasterized separately onto each target grid with the same
pixel-center rule (rasterio.features.rasterize), so the two masks always
describe exactly the same ground area.

The screenshot covers exactly the same lon/lat rectangle as the GeoTIFF's
pixel grid (see capture_basemap_reference), and is saved with a world file
(.pgw + .prj, EPSG:3857) so it is georeferenced outside this app too.
"""

from __future__ import annotations

import io
import json
import math
import shutil
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

import numpy as np
import rasterio
import rasterio.features
import rasterio.warp
import requests
from PIL import Image, ImageDraw
from rasterio.transform import Affine
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Manual labeling classes. 255 = unlabeled / ignore (never a real class).
DEFAULT_LABEL_CLASSES = [
    {"id": 0, "key": "water", "label": "Water", "color": "#2775CA"},
    {"id": 1, "key": "forest_tree", "label": "Forest / Tree", "color": "#1E7A34"},
    {"id": 2, "key": "grass_crop", "label": "Grass / Crop", "color": "#8BCA52"},
    {"id": 3, "key": "bare_mud_soil", "label": "Bare / Mud / Soil", "color": "#C2973F"},
    {"id": 4, "key": "sand", "label": "Sand", "color": "#E8D9A0"},
    {"id": 5, "key": "building", "label": "Building", "color": "#D62728"},
    {"id": 6, "key": "road", "label": "Road", "color": "#808080"},
    {"id": 7, "key": "shrub", "label": "Shrub", "color": "#7A7A2E"},
    {"id": 8, "key": "shadow", "label": "Shadow", "color": "#3D3D3D"},
    {"id": 9, "key": "unknown", "label": "Unknown", "color": "#FFFFFF"},
]
IGNORE_LABEL_VALUE = 255
_CLASS_BY_ID = {entry["id"]: entry for entry in DEFAULT_LABEL_CLASSES}

# 10-class manual scheme -> the existing 6-class U-Net scheme (Water=0,
# Grass=1, Shrub=2, Sparse Forest=3, Dense Forest=4, Bare=5). Classes with
# no 6-class equivalent go to Bare (5).
LABEL_TO_SIX_CLASS_MAP = {
    "water": 0,
    "grass_crop": 1,
    "shrub": 2,
    "forest_tree": 4,
    "bare_mud_soil": 5,
    "sand": 5,
    "building": 5,
    "road": 5,
    "shadow": 5,
    "unknown": 5,
}

# ---------------------------------------------------------------------------
# Web Mercator tile math (Esri / Leaflet convention: 256 px tiles)
# ---------------------------------------------------------------------------

ESRI_WORLD_IMAGERY_TILE_URL = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "World_Imagery/MapServer/tile/{z}/{y}/{x}"
)
TILE_SIZE_PX = 256
EARTH_RADIUS_M = 6378137.0
ORIGIN_SHIFT_M = math.pi * EARTH_RADIUS_M

MAX_SCREENSHOT_DIMENSION_PX = 4096  # long side; highest zoom that fits is used
MAX_ZOOM = 19
MIN_ACCEPTABLE_ZOOM = 15  # ~4.5 m/px; coarser than this is no longer "high-resolution"
MAX_TILE_COUNT = 400
TILE_FETCH_WORKERS = 8


def _lonlat_to_world_pixel(lon: float, lat: float, zoom: int) -> tuple[float, float]:
    n = 2 ** zoom
    x = (lon + 180.0) / 360.0 * n * TILE_SIZE_PX
    lat_rad = math.radians(max(min(lat, 85.05112878), -85.05112878))
    y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n * TILE_SIZE_PX
    return x, y


def _world_pixel_to_lonlat(x: float, y: float, zoom: int) -> tuple[float, float]:
    n = 2 ** zoom
    lon = x / (n * TILE_SIZE_PX) * 360.0 - 180.0
    y_fraction = 1.0 - 2.0 * y / (n * TILE_SIZE_PX)
    lat = math.degrees(math.atan(math.sinh(math.pi * y_fraction)))
    return lon, lat


def _mercator_resolution_m(zoom: int) -> float:
    """Metres per world pixel in EPSG:3857 at this zoom."""
    return 2 * ORIGIN_SHIFT_M / (TILE_SIZE_PX * 2 ** zoom)


# ---------------------------------------------------------------------------
# Placeholder / invalid tile detection
#
# Esri answers HTTP 200 with a flat gray JPEG reading "Map data not yet
# available" (2521 bytes, ~94% of pixels exactly RGB 204,204,204) wherever
# it has no imagery at the requested zoom -- verified against live tiles
# over Dhaka z20, Sundarbans z19, Chittagong Hill Tracts z19 and the Bay of
# Bengal z17. A tile is rejected when it is mostly that gray, or when it is
# almost perfectly uniform (blank / "no data" tiles of any color).
# ---------------------------------------------------------------------------

PLACEHOLDER_GRAY = 204
PLACEHOLDER_GRAY_TOLERANCE = 4
PLACEHOLDER_PIXEL_FRACTION = 0.6
BLANK_TILE_STD_MAX = 2.0


def tile_validity_problem(image: Image.Image) -> Optional[str]:
    """None if the tile looks like real imagery, otherwise the reason."""
    if max(image.size) > 1024:
        # Whole-screenshot check: a reduced copy is enough to spot a blank or
        # placeholder image and avoids a ~100 MB int16 copy (every individual
        # tile was already checked at full resolution).
        image = image.copy()
        image.thumbnail((1024, 1024))
    arr = np.asarray(image.convert("RGB"), dtype=np.int16)
    if float(arr.std()) < BLANK_TILE_STD_MAX:
        return "blank / no-data tile"
    near_gray = np.all(np.abs(arr - PLACEHOLDER_GRAY) <= PLACEHOLDER_GRAY_TOLERANCE, axis=-1)
    if float(near_gray.mean()) >= PLACEHOLDER_PIXEL_FRACTION:
        return "'Map data not yet available' placeholder tile"
    return None


def _http_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=4, backoff_factor=0.6, status_forcelist=(429, 500, 502, 503, 504))
    adapter = HTTPAdapter(max_retries=retry, pool_connections=TILE_FETCH_WORKERS, pool_maxsize=TILE_FETCH_WORKERS)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers["User-Agent"] = "February-Dataset-Labeling/1.0"
    return session


def _fetch_tiles(session, tile_url_template: str, zoom: int, tiles: list[tuple[int, int]], on_tile) -> None:
    """Download tiles in parallel and hand each one to on_tile(tile, image)
    as soon as it arrives, so only a few tiles are ever held in memory."""
    def fetch(tile):
        tile_x, tile_y = tile
        response = session.get(tile_url_template.format(z=zoom, x=tile_x, y=tile_y), timeout=30)
        response.raise_for_status()
        return tile, Image.open(io.BytesIO(response.content)).convert("RGB")

    with ThreadPoolExecutor(max_workers=TILE_FETCH_WORKERS) as pool:
        for tile, image in pool.map(fetch, tiles):
            on_tile(tile, image)


# ---------------------------------------------------------------------------
# Screenshot capture
# ---------------------------------------------------------------------------

def capture_basemap_reference(
    coordinates: list,
    output_path: Path,
    tile_url_template: str = ESRI_WORLD_IMAGERY_TILE_URL,
    max_dimension_px: int = MAX_SCREENSHOT_DIMENSION_PX,
    mask_to_polygon: bool = False,
) -> dict[str, Any]:
    """Capture a clean, high-resolution basemap screenshot of exactly the
    same lon/lat rectangle as the AOI's GeoTIFF grid.

    * Uses the highest zoom (<= MAX_ZOOM) whose crop fits max_dimension_px.
    * If ANY tile at that zoom is a placeholder/blank tile, steps down one
      zoom level and retries; raises if no zoom >= MIN_ACCEPTABLE_ZOOM is
      fully valid. A screenshot containing "Map data not yet available" or
      "no data" is therefore never written to disk.
    * The image is CLEAN -- no text, outline or other overlay is burned in,
      so it can be used directly as model input. The AOI outline is
      returned as pixel coordinates (aoi_pixels) for display only.
    * If mask_to_polygon is True and the AOI's real coordinates describe a
      non-rectangular shape, pixels outside that polygon are painted white
      -- so the saved PNG shows the plot's actual surveyed shape, not just
      its rectangular bounding crop. A plot whose coordinates ARE already a
      (lon/lat-aligned) rectangle is visually unaffected.
    * Writes <name>.pgw + <name>.prj (EPSG:3857) next to the PNG.
    """
    from services.historical_collection_service import compute_download_grid

    grid = compute_download_grid(coordinates)
    west = grid["west"]
    north = grid["north"]
    east = west + grid["width"] * grid["pixel_size"]
    south = north - grid["height"] * grid["pixel_size"]

    start_zoom = MAX_ZOOM
    for zoom in range(MAX_ZOOM, 0, -1):
        x_min, y_min = _lonlat_to_world_pixel(west, north, zoom)
        x_max, y_max = _lonlat_to_world_pixel(east, south, zoom)
        start_zoom = zoom
        if max(x_max - x_min, y_max - y_min) <= max_dimension_px:
            break

    session = _http_session()
    rejected = []
    for zoom in range(start_zoom, 0, -1):
        if zoom < MIN_ACCEPTABLE_ZOOM and zoom < start_zoom:
            break
        x_min, y_min = _lonlat_to_world_pixel(west, north, zoom)
        x_max, y_max = _lonlat_to_world_pixel(east, south, zoom)
        # Whole-pixel crop; the georeferencing below describes exactly this
        # rounded crop, so there is no hidden sub-pixel offset.
        crop_x0, crop_y0 = int(round(x_min)), int(round(y_min))
        crop_x1, crop_y1 = max(int(round(x_max)), crop_x0 + 1), max(int(round(y_max)), crop_y0 + 1)

        tile_x_min, tile_x_max = crop_x0 // TILE_SIZE_PX, (crop_x1 - 1) // TILE_SIZE_PX
        tile_y_min, tile_y_max = crop_y0 // TILE_SIZE_PX, (crop_y1 - 1) // TILE_SIZE_PX
        tiles = [(tx, ty) for tx in range(tile_x_min, tile_x_max + 1) for ty in range(tile_y_min, tile_y_max + 1)]
        if len(tiles) > MAX_TILE_COUNT:
            continue

        mosaic = Image.new("RGB", ((tile_x_max - tile_x_min + 1) * TILE_SIZE_PX, (tile_y_max - tile_y_min + 1) * TILE_SIZE_PX))
        bad = {}

        def place(tile, image):
            reason = tile_validity_problem(image)
            if reason:
                bad[tile] = reason
            else:
                mosaic.paste(image, ((tile[0] - tile_x_min) * TILE_SIZE_PX, (tile[1] - tile_y_min) * TILE_SIZE_PX))

        _fetch_tiles(session, tile_url_template, zoom, tiles, place)
        if bad:
            del mosaic
            reason = next(iter(bad.values()))
            rejected.append(f"zoom {zoom}: {len(bad)}/{len(tiles)} tiles invalid ({reason})")
            print(f"Screenshot: zoom {zoom} rejected -- {len(bad)}/{len(tiles)} tiles invalid ({reason}); trying zoom {zoom - 1}.")
            continue

        offset_x, offset_y = tile_x_min * TILE_SIZE_PX, tile_y_min * TILE_SIZE_PX
        screenshot = mosaic.crop((crop_x0 - offset_x, crop_y0 - offset_y, crop_x1 - offset_x, crop_y1 - offset_y))
        del mosaic

        problem = tile_validity_problem(screenshot)
        if problem:
            rejected.append(f"zoom {zoom}: final image invalid ({problem})")
            continue

        return _save_screenshot(screenshot, output_path, coordinates, zoom, crop_x0, crop_y0, grid, tile_url_template,
                                 mask_to_polygon=mask_to_polygon)

    raise RuntimeError(
        "No valid high-resolution basemap imagery is available for this area "
        f"(checked zoom {start_zoom} down to {MIN_ACCEPTABLE_ZOOM}: " + "; ".join(rejected or ["too many tiles"]) +
        "). No screenshot was saved."
    )


def _mask_screenshot_to_polygon(screenshot, polygon_pixels: list[tuple[float, float]]):
    """Paints every pixel outside polygon_pixels white. polygon_pixels must
    already be in this screenshot's own pixel space (post-crop)."""
    if len(polygon_pixels) < 3:
        return screenshot
    mask = Image.new("L", screenshot.size, 0)
    ImageDraw.Draw(mask).polygon([tuple(p) for p in polygon_pixels], fill=255)
    white = Image.new("RGB", screenshot.size, (255, 255, 255))
    return Image.composite(screenshot, white, mask)


def _save_screenshot(screenshot, output_path: Path, coordinates, zoom, crop_x0, crop_y0, grid, tile_url_template,
                      mask_to_polygon: bool = False) -> dict[str, Any]:
    pre_mask_info = {
        "zoom": zoom, "origin_world_px_x": crop_x0, "origin_world_px_y": crop_y0,
    }
    polygon_pixels = lonlat_to_screenshot_pixels(close_polygon_ring(coordinates), pre_mask_info)
    if mask_to_polygon:
        screenshot = _mask_screenshot_to_polygon(screenshot, polygon_pixels)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_name(output_path.name + ".part")
    screenshot.save(temp_path, format="PNG", optimize=False)
    temp_path.replace(output_path)

    resolution = _mercator_resolution_m(zoom)
    x_left_m = crop_x0 * resolution - ORIGIN_SHIFT_M
    y_top_m = ORIGIN_SHIFT_M - crop_y0 * resolution
    transform_3857 = [resolution, 0.0, x_left_m, 0.0, -resolution, y_top_m]
    _write_world_file(output_path, transform_3857)

    width, height = screenshot.size
    west, north = _world_pixel_to_lonlat(crop_x0, crop_y0, zoom)
    east, south = _world_pixel_to_lonlat(crop_x0 + width, crop_y0 + height, zoom)
    center_lat = (north + south) / 2
    info = {
        "file_name": output_path.name,
        "width": width,
        "height": height,
        "zoom": zoom,
        "origin_world_px_x": crop_x0,
        "origin_world_px_y": crop_y0,
        "crs": "EPSG:3857",
        "transform_3857": transform_3857,
        "bounds_lonlat": [west, south, east, north],
        "geotiff_grid_bounds_lonlat": [
            grid["west"], grid["north"] - grid["height"] * grid["pixel_size"],
            grid["west"] + grid["width"] * grid["pixel_size"], grid["north"],
        ],
        "ground_resolution_m": resolution * math.cos(math.radians(center_lat)),
        "tile_url_template": tile_url_template,
        "clean": True,
        "validated": True,
        "masked_to_polygon": mask_to_polygon,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    info["aoi_pixels"] = [list(point) for point in polygon_pixels]
    return info


def _write_world_file(image_path: Path, transform: list[float]) -> None:
    """ESRI world file (.pgw) + .prj. World files reference the CENTER of the
    top-left pixel."""
    a, _, c, _, e, f = transform
    lines = [a, 0.0, 0.0, e, c + a / 2, f + e / 2]
    image_path.with_suffix(".pgw").write_text("\n".join(f"{value:.10f}" for value in lines) + "\n", encoding="ascii")
    image_path.with_suffix(".prj").write_text(rasterio.crs.CRS.from_epsg(3857).to_wkt(), encoding="ascii")


def screenshot_path_for(job_directory: Path, reference_info: dict[str, Any]) -> Path:
    """New jobs store the screenshot under its own name; older jobs used
    labeling_reference.png."""
    return job_directory / (reference_info.get("file_name") or "labeling_reference.png")


# ---------------------------------------------------------------------------
# Coordinate conversions (all polygons pass through EPSG:4326 lon/lat)
# ---------------------------------------------------------------------------

def close_polygon_ring(coordinates: list) -> list:
    ring = [list(point) for point in coordinates]
    if ring and tuple(ring[0]) != tuple(ring[-1]):
        ring = ring + [ring[0]]
    return ring


def screenshot_pixels_to_lonlat(points: Iterable, reference_info: dict[str, Any]) -> list[list[float]]:
    zoom = reference_info["zoom"]
    origin_x = reference_info["origin_world_px_x"]
    origin_y = reference_info["origin_world_px_y"]
    return [list(_world_pixel_to_lonlat(origin_x + float(px), origin_y + float(py), zoom)) for px, py in points]


def lonlat_to_screenshot_pixels(points: Iterable, reference_info: dict[str, Any]) -> list[tuple[float, float]]:
    zoom = reference_info["zoom"]
    origin_x = reference_info["origin_world_px_x"]
    origin_y = reference_info["origin_world_px_y"]
    result = []
    for lon, lat in points:
        world_x, world_y = _lonlat_to_world_pixel(float(lon), float(lat), zoom)
        result.append((world_x - origin_x, world_y - origin_y))
    return result


def _raster_georef(tif_path: Path) -> tuple[Affine, Any, int, int]:
    with rasterio.open(tif_path) as src:
        return src.transform, src.crs, src.width, src.height


def _lonlat_to_crs(points: list, crs) -> list[tuple[float, float]]:
    lons = [float(p[0]) for p in points]
    lats = [float(p[1]) for p in points]
    if crs is not None and str(crs) != "EPSG:4326":
        xs, ys = rasterio.warp.transform("EPSG:4326", crs, lons, lats)
        return list(zip(xs, ys))
    return list(zip(lons, lats))


def polygons_to_lonlat(
    polygons: list[dict[str, Any]],
    reference_mode: str,
    reference_info: dict[str, Any],
    preview_info: Optional[dict[str, Any]],
    tif_path: Optional[Path],
) -> list[dict[str, Any]]:
    """Convert annotator polygons (pixel coordinates on whatever image was
    displayed) into lon/lat polygons -- the single canonical label set."""
    if reference_mode in PREVIEW_MODES:
        if preview_info is None or tif_path is None:
            raise ValueError("The GeoTIFF preview used for drawing is not available any more -- reload the page.")
        transform, crs, _, _ = _raster_georef(tif_path)
        scale = preview_info["scale"]

        def to_lonlat(points):
            projected = [transform * (float(x) / scale, float(y) / scale) for x, y in points]
            if crs is not None and str(crs) != "EPSG:4326":
                lons, lats = rasterio.warp.transform(crs, "EPSG:4326", [p[0] for p in projected], [p[1] for p in projected])
                return [list(p) for p in zip(lons, lats)]
            return [list(p) for p in projected]
    else:
        def to_lonlat(points):
            return screenshot_pixels_to_lonlat(points, reference_info)

    result = []
    for polygon in polygons:
        points = polygon.get("points") or []
        class_id = polygon.get("class_id")
        if len(points) < 3 or class_id not in _CLASS_BY_ID:
            continue
        ring = to_lonlat(points)
        ring.append(list(ring[0]))
        result.append({"class_id": int(class_id), "ring": ring})
    return result


# ---------------------------------------------------------------------------
# Rasterization (same pixel-center rule for every grid)
# ---------------------------------------------------------------------------

def _rasterize(shapes: list[tuple[dict, int]], width: int, height: int, transform: Affine, fill: int) -> np.ndarray:
    if not shapes:
        return np.full((height, width), fill, dtype=np.uint8)
    # Later shapes overwrite earlier ones, so a polygon drawn on top of
    # another wins -- the same behavior as the drawing canvas.
    return rasterio.features.rasterize(
        shapes, out_shape=(height, width), transform=transform, fill=fill, dtype="uint8", all_touched=False
    )


def rasterize_on_geotiff_grid(lonlat_polygons: list[dict[str, Any]], tif_path: Path) -> np.ndarray:
    transform, crs, width, height = _raster_georef(tif_path)
    shapes = [({"type": "Polygon", "coordinates": [_lonlat_to_crs(p["ring"], crs)]}, p["class_id"]) for p in lonlat_polygons]
    return _rasterize(shapes, width, height, transform, IGNORE_LABEL_VALUE)


def rasterize_on_screenshot_grid(lonlat_polygons: list[dict[str, Any]], reference_info: dict[str, Any]) -> np.ndarray:
    shapes = [
        ({"type": "Polygon", "coordinates": [lonlat_to_screenshot_pixels(p["ring"], reference_info)]}, p["class_id"])
        for p in lonlat_polygons
    ]
    return _rasterize(shapes, reference_info["width"], reference_info["height"], Affine.identity(), IGNORE_LABEL_VALUE)


def aoi_mask_on_screenshot_grid(coordinates: list, reference_info: dict[str, Any]) -> np.ndarray:
    ring = lonlat_to_screenshot_pixels(close_polygon_ring(coordinates), reference_info)
    shape = [({"type": "Polygon", "coordinates": [ring]}, 1)]
    return _rasterize(shape, reference_info["width"], reference_info["height"], Affine.identity(), 0).astype(bool)


def compute_valid_and_aoi_masks(tif_path: Path, coordinates: list) -> tuple[np.ndarray, np.ndarray]:
    """(valid_mask, aoi_mask) on the GeoTIFF grid: valid = every band finite,
    not nodata and not all-zero; aoi = pixel center inside the AOI polygon."""
    with rasterio.open(tif_path) as src:
        stack = src.read().astype(np.float32)
        nodata = src.nodata
        transform, crs, width, height = src.transform, src.crs, src.width, src.height

    valid = np.isfinite(stack).all(axis=0)
    if nodata is not None and np.isfinite(nodata):
        valid &= ~np.isclose(stack, nodata).any(axis=0)
    magnitude = np.nan_to_num(stack, nan=0.0, posinf=0.0, neginf=0.0)
    valid &= np.max(np.abs(magnitude), axis=0) > 1e-6

    ring = _lonlat_to_crs(close_polygon_ring(coordinates), crs)
    aoi = _rasterize([({"type": "Polygon", "coordinates": [ring]}, 1)], width, height, transform, 0).astype(bool)
    return valid, aoi


def enforce_valid_labels(
    mask_array: np.ndarray,
    allowed_mask: np.ndarray,
    ignore_value: int = IGNORE_LABEL_VALUE,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Set every pixel outside `allowed_mask` to ignore_value; never touch a
    pixel inside it. Returns (corrected_mask, stats)."""
    user_labeled = mask_array != ignore_value
    overridden = user_labeled & ~allowed_mask
    corrected = mask_array.copy()
    corrected[~allowed_mask] = ignore_value

    user_labeled_count = int(user_labeled.sum())
    overridden_count = int(overridden.sum())
    final_labeled_count = int((corrected != ignore_value).sum())
    class_ids, class_counts = np.unique(corrected[corrected != ignore_value], return_counts=True)
    return corrected, {
        "total_pixels": int(mask_array.size),
        "user_labeled_pixel_count": user_labeled_count,
        "valid_labeled_pixel_count": final_labeled_count,
        "ignored_pixel_count": int(mask_array.size) - final_labeled_count,
        "overridden_outside_valid_region_count": overridden_count,
        "overridden_outside_valid_region_fraction": overridden_count / user_labeled_count if user_labeled_count else 0.0,
        "class_distribution": {int(cid): int(count) for cid, count in zip(class_ids, class_counts)},
    }


def remap_to_six_class_mask(mask_array: np.ndarray, ignore_value: int = IGNORE_LABEL_VALUE) -> np.ndarray:
    remapped = np.full_like(mask_array, ignore_value)
    for class_id, entry in _CLASS_BY_ID.items():
        six_class_id = LABEL_TO_SIX_CLASS_MAP.get(entry["key"])
        if six_class_id is not None:
            remapped[mask_array == class_id] = six_class_id
    return remapped


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def backup_existing_file(path: Path) -> Optional[Path]:
    """Copy an existing file to backups/<name>.<timestamp><ext> before it is
    overwritten."""
    if not path.exists():
        return None
    backup_dir = path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_path = backup_dir / f"{path.stem}.{stamp}{path.suffix}"
    shutil.copy2(path, backup_path)
    return backup_path


def save_label_png(mask_array: np.ndarray, output_path: Path) -> None:
    backup_existing_file(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(mask_array, mode="L").save(output_path, format="PNG")


def save_label_geotiff(mask_array: np.ndarray, reference_tif: Path, output_path: Path) -> None:
    """Single-band uint8 mask with the GeoTIFF's exact CRS + transform."""
    backup_existing_file(output_path)
    with rasterio.open(reference_tif) as src:
        transform, crs = src.transform, src.crs
    with rasterio.open(
        output_path, "w", driver="GTiff", width=mask_array.shape[1], height=mask_array.shape[0],
        count=1, dtype="uint8", crs=crs, transform=transform, nodata=IGNORE_LABEL_VALUE, compress="deflate",
    ) as dst:
        dst.write(mask_array, 1)
        dst.set_band_description(1, "land_cover_class (255 = ignore)")


def copy_world_file(source_image: Path, target_image: Path) -> None:
    for suffix in (".pgw", ".prj"):
        source = source_image.with_suffix(suffix)
        if source.exists():
            shutil.copy2(source, target_image.with_suffix(suffix))


def save_color_overlay(base_image_path: Path, mask_array: np.ndarray, output_path: Path, alpha: float = 0.45,
                       rows_per_chunk: int = 256) -> None:
    """Human-check image: the class colors blended over the screenshot.
    Integer blend of only the labeled pixels, a slice of rows at a time,
    so it needs little memory even for a 4096 px screenshot."""
    image = np.array(Image.open(base_image_path).convert("RGB"), dtype=np.uint8)  # writable copy
    colors = np.zeros((256, 3), dtype=np.uint16)
    for class_id, entry in _CLASS_BY_ID.items():
        hex_value = entry["color"].lstrip("#")
        colors[class_id] = [int(hex_value[i:i + 2], 16) for i in (0, 2, 4)]
    a = int(round(alpha * 256))
    for start in range(0, image.shape[0], rows_per_chunk):
        rows = slice(start, start + rows_per_chunk)
        block_mask = mask_array[rows]
        labeled = block_mask != IGNORE_LABEL_VALUE
        if not labeled.any():
            continue
        block = image[rows]
        base = block[labeled].astype(np.uint16)
        block[labeled] = ((base * (256 - a) + colors[block_mask[labeled]] * a) >> 8).astype(np.uint8)
    Image.fromarray(image, mode="RGB").save(output_path, format="PNG")


def write_labels_geojson(
    lonlat_polygons: list[dict[str, Any]],
    output_path: Path,
    properties: dict[str, Any],
) -> None:
    features = []
    for index, polygon in enumerate(lonlat_polygons, start=1):
        entry = _CLASS_BY_ID[polygon["class_id"]]
        features.append({
            "type": "Feature",
            "properties": {
                "polygon_index": index,
                "class_id": entry["id"],
                "class_key": entry["key"],
                "class_name": entry["label"],
                "color": entry["color"],
                "six_class_id": LABEL_TO_SIX_CLASS_MAP.get(entry["key"]),
            },
            "geometry": {"type": "Polygon", "coordinates": [[[round(x, 9), round(y, 9)] for x, y in polygon["ring"]]]},
        })
    backup_existing_file(output_path)
    output_path.write_text(json.dumps({
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "properties": properties,
        "features": features,
    }, indent=2), encoding="utf-8")


def lonlat_polygons_to_screenshot_pixels(lonlat_polygons: list[dict[str, Any]], reference_info: dict[str, Any]) -> list[dict[str, Any]]:
    """For reloading saved labels back onto the drawing canvas."""
    return [
        {"class_id": p["class_id"], "points": [list(pt) for pt in lonlat_to_screenshot_pixels(p["ring"][:-1], reference_info)]}
        for p in lonlat_polygons
    ]


def read_labels_geojson(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        {"class_id": int(feature["properties"]["class_id"]), "ring": feature["geometry"]["coordinates"][0]}
        for feature in data.get("features", [])
        if feature.get("geometry", {}).get("type") == "Polygon"
    ]


def build_dataset_zip(zip_output_path: Path, entries: list[tuple[Path, str]], extra_text_files: dict[str, str]) -> Path:
    """Write the ZIP atomically. GeoTIFFs/PNGs are already compressed, so
    they are stored rather than deflated again -- much faster."""
    zip_output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = zip_output_path.with_name(zip_output_path.name + ".part")
    with zipfile.ZipFile(temp_path, "w") as archive:
        for source, arcname in entries:
            if source.exists():
                compress = zipfile.ZIP_STORED if source.suffix.lower() in {".tif", ".png"} else zipfile.ZIP_DEFLATED
                archive.write(source, arcname=arcname, compress_type=compress)
        for arcname, text in extra_text_files.items():
            archive.writestr(arcname, text.encode("utf-8"), compress_type=zipfile.ZIP_DEFLATED)
    temp_path.replace(zip_output_path)
    return zip_output_path


# ---------------------------------------------------------------------------
# GeoTIFF-native previews (True RGB / NDVI / SAR false-color) rendered from
# the GeoTIFF's own bands, upscaled by an integer factor for drawing.
# ---------------------------------------------------------------------------

PREVIEW_MODES = ("rgb", "ndvi", "false_color")
PREVIEW_TARGET_LONG_SIDE_PX = 1400
AOI_OUTLINE_COLOR = (255, 221, 0)
AOI_OUTSIDE_SHADE_ALPHA = 0.55


def _shared_percentile_stretch(bands: list[np.ndarray], low_pct: float = 2.0, high_pct: float = 98.0) -> list[np.ndarray]:
    """One shared stretch across all bands (a per-band stretch gives an
    unnatural color cast)."""
    finite_values = [band[np.isfinite(band)] for band in bands]
    finite_values = [values for values in finite_values if values.size]
    if not finite_values:
        return [np.zeros_like(band, dtype=np.uint8) for band in bands]
    low, high = np.percentile(np.concatenate(finite_values), [low_pct, high_pct])
    if high <= low:
        high = low + 1.0
    return [(np.clip((np.nan_to_num(band, nan=low, posinf=high, neginf=low) - low) / (high - low), 0.0, 1.0) * 255).astype(np.uint8) for band in bands]


def _render_true_color(stack: np.ndarray) -> Image.Image:
    red, green, blue = _shared_percentile_stretch([stack[0], stack[1], stack[2]])
    return Image.fromarray(np.dstack([red, green, blue]), mode="RGB")


def _render_ndvi(stack: np.ndarray) -> Image.Image:
    ndvi = np.clip(np.nan_to_num(stack[3], nan=0.0, posinf=0.0, neginf=0.0), -1.0, 1.0)
    t = (ndvi + 1.0) / 2.0
    low = np.array([120, 83, 48], dtype=np.float32)
    mid = np.array([235, 220, 150], dtype=np.float32)
    high = np.array([20, 110, 40], dtype=np.float32)
    mix_low = (t / 0.5)[..., None]
    mix_high = ((t - 0.5) / 0.5)[..., None]
    rgb = np.where(
        (t < 0.5)[..., None],
        low[None, None, :] * (1 - mix_low) + mid[None, None, :] * mix_low,
        mid[None, None, :] * (1 - mix_high) + high[None, None, :] * mix_high,
    )
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), mode="RGB")


def _render_sar_false_color(stack: np.ndarray) -> Image.Image:
    vv, vh, ratio = _shared_percentile_stretch([stack[6], stack[7], stack[8]])
    return Image.fromarray(np.dstack([vv, vh, ratio]), mode="RGB")


def generate_labeling_previews(tif_path: Path, coordinates: list, output_dir: Path, year: int) -> dict[str, Any]:
    with rasterio.open(tif_path) as src:
        stack = src.read().astype(np.float32)
        native_width, native_height = src.width, src.height
        transform, crs = src.transform, src.crs

    valid_mask, aoi_mask = compute_valid_and_aoi_masks(tif_path, coordinates)
    scale = max(1, round(PREVIEW_TARGET_LONG_SIDE_PX / max(native_width, native_height)))
    display_width, display_height = native_width * scale, native_height * scale

    ring = [(~transform) * point for point in _lonlat_to_crs(close_polygon_ring(coordinates), crs)]
    display_ring = [(x * scale, y * scale) for x, y in ring]

    renderers = {"rgb": _render_true_color, "ndvi": _render_ndvi, "false_color": _render_sar_false_color}
    output_dir.mkdir(parents=True, exist_ok=True)
    preview_paths: dict[str, Path] = {}
    for mode, renderer in renderers.items():
        rgb_array = np.array(renderer(stack).convert("RGB"), dtype=np.float32)
        rgb_array[~aoi_mask] *= (1.0 - AOI_OUTSIDE_SHADE_ALPHA)
        image = Image.fromarray(rgb_array.astype(np.uint8), mode="RGB")
        if scale > 1:
            image = image.resize((display_width, display_height), Image.NEAREST)
        ImageDraw.Draw(image).line(display_ring, fill=AOI_OUTLINE_COLOR, width=max(2, scale), joint="curve")
        path = output_dir / f"labeling_preview_{year}_{mode}.png"
        image.save(path, format="PNG")
        preview_paths[mode] = path

    return {
        "source": "geotiff_native",
        "year": year,
        "width": display_width,
        "height": display_height,
        "native_width": native_width,
        "native_height": native_height,
        "scale": scale,
        "modes": list(renderers.keys()),
        "paths": {mode: str(path) for mode, path in preview_paths.items()},
        "valid_pixel_fraction": float(valid_mask.mean()),
        "aoi_pixel_fraction": float(aoi_mask.mean()),
    }
