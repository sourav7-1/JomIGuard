"""February 2025 dataset collection: one 10-band Sentinel-1/Sentinel-2
GeoTIFF + one matching high-resolution basemap screenshot per selected area.

Only 2025 imagery is collected. The year is fixed server-side
(COLLECTION_YEAR); nothing the browser sends can change it.

Job lifecycle (per year record -- a job has exactly one, for 2025):
    QUEUED -> PROCESSING -> EXPORTING -> READY -> DOWNLOADED
                                       -> FAILED (-> RETRYING -> ...)

The GeoTIFF and the screenshot are produced in parallel background threads
so neither blocks the Flask request cycle or waits on the other. Every job
is persisted to historical_datasets/<job_id>/job.json and reloaded at
startup, so jobs survive a server restart.
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

import ee
import numpy as np
import requests

from services.earth_engine_service import (
    FINAL_BAND_ORDER,
    build_quality_warnings,
    close_polygon,
    compute_quality_flag,
    get_collection_acquisition_metadata,
    get_period_quality_metrics,
    mask_sentinel2,
    validate_coordinates,
)

BASE_DIR = Path(__file__).resolve().parent.parent

# Where every job's files live. On a server, point DATA_DIR at a persistent
# disk (e.g. /var/data/historical_datasets on Render) so data survives
# restarts and redeploys.
DATASETS_DIR = Path(os.environ.get("DATA_DIR") or BASE_DIR / "collected")
DATASETS_DIR.mkdir(parents=True, exist_ok=True)


def _mirror_dir() -> Optional[Path]:
    """Extra copy of every job folder. Default on a local machine: one level
    above this App folder (the original project's behavior). Default on
    Render: off. MIRROR_DIR=<path> overrides, MIRROR_DIR=off disables.
    Mirroring is incremental and never includes the ZIP or backups."""
    setting = os.environ.get("MIRROR_DIR", "").strip()
    if setting.lower() in {"off", "none", "false", "0"}:
        return None
    if setting:
        return Path(setting)
    # Off by default in this project: everything stays inside ./collected.
    return None


EXTERNAL_MIRROR_DIR: Optional[Path] = _mirror_dir()

# ---------------------------------------------------------------------------
# Collection period: February 2025 ONLY.
# ---------------------------------------------------------------------------
COLLECTION_YEAR = 2025
DEFAULT_MONTH = 2  # February
DEFAULT_DAY_START = 1
DEFAULT_DAY_END = 28

# Bounded cloud-threshold retry ladder. A more permissive threshold is only
# tried when the stricter one produced no usable composite.
DEFAULT_CLOUD_THRESHOLD_LADDER = [20, 40, 60, 80, 100]
MAX_RETRY_ATTEMPTS = 6

# ---------------------------------------------------------------------------
# GeoTIFF download grid. Every GeoTIFF is requested on an explicit EPSG:4326
# pixel grid (10 m expressed in degrees, the same conversion Earth Engine
# applies for scale=10 in EPSG:4326) whose origin is snapped to a multiple
# of the pixel size. Earth Engine refuses single downloads above ~48 MB, so
# larger areas are split into chunks on that same grid, fetched in
# parallel, and stitched back together pixel-exactly.
# ---------------------------------------------------------------------------
PIXEL_SIZE_DEG = 10.0 / 111319.49079327357
BYTES_PER_PIXEL = 4 * len(FINAL_BAND_ORDER)  # float32 x 10 bands
MAX_CHUNK_BYTES = 30 * 1024 * 1024
MAX_CHUNK_SIDE_PX = int(math.sqrt(MAX_CHUNK_BYTES / BYTES_PER_PIXEL))
# Hard cap on GeoTIFF size (pixels at 10 m). The whole 10-band float32 stack
# is held in memory while stitching (40 bytes/pixel), so a small server
# needs a lower cap: e.g. MAX_TOTAL_PIXELS=4000000 (~160 MB) on a 512 MB
# instance. Default ~2.4 GB, fine on a normal PC.
MAX_TOTAL_PIXELS = int(os.environ.get("MAX_TOTAL_PIXELS") or 60_000_000)

# On a server whose disk is only scratch space, delete jobs older than this
# many hours (checked whenever a new job starts). Unset = keep forever.
JOB_RETENTION_HOURS = float(os.environ.get("JOB_RETENTION_HOURS") or 0)
DOWNLOAD_WORKERS = 4
DOWNLOAD_RETRIES = 3

JOBS: dict[str, "HistoricalJob"] = {}
_JOBS_LOCK = threading.Lock()


def collection_period() -> dict[str, Any]:
    return {
        "year": COLLECTION_YEAR,
        "start_date": f"{COLLECTION_YEAR:04d}-{DEFAULT_MONTH:02d}-{DEFAULT_DAY_START:02d}",
        "end_date": f"{COLLECTION_YEAR:04d}-{DEFAULT_MONTH:02d}-{DEFAULT_DAY_END:02d}",
    }


def sanitize_area_name(area_name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_\-]+", "_", (area_name or "").strip())
    cleaned = re.sub(r"_{2,}", "_", cleaned).strip("_")
    return cleaned or "Selected_Area"


def scene_stem(safe_area_name: str, year: int) -> str:
    """Shared filename stem for every file belonging to one area/year, so
    the GeoTIFF, screenshot, masks and GeoJSON always pair up by name."""
    return f"{safe_area_name}_{year}_S1_S2_Feb"


# ---------------------------------------------------------------------------
# Composite building (reuses earth_engine_service helpers)
# ---------------------------------------------------------------------------

def _build_evi(s2_median):
    """EVI with Sentinel-2 SR reflectance scaled to 0..1 (the '+1' term in
    the denominator does not cancel the 10000 DN scale)."""
    return s2_median.expression(
        "2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))",
        {
            "NIR": s2_median.select("B8").divide(10000),
            "RED": s2_median.select("B4").divide(10000),
            "BLUE": s2_median.select("B2").divide(10000),
        },
    ).rename("EVI")


def _build_yearly_stack(selected_area, start_date: str, end_date_exclusive: str, cloud_percentage: float):
    """One 10-band composite at a given cloud threshold, or None when no
    Sentinel-2 scene passes the cloud filter."""
    s2_collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(selected_area)
        .filterDate(start_date, end_date_exclusive)
        .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", cloud_percentage))
    )
    s2_count, s2_dates = get_collection_acquisition_metadata(s2_collection)
    if s2_count == 0:
        return None

    s2_median = s2_collection.map(mask_sentinel2).median().clip(selected_area)
    quality_metrics = get_period_quality_metrics(s2_collection, s2_median, selected_area)

    ndvi = s2_median.normalizedDifference(["B8", "B4"]).rename("NDVI")
    evi = _build_evi(s2_median)
    nbr = s2_median.normalizedDifference(["B8", "B12"]).rename("NBR")

    s1_collection = (
        ee.ImageCollection("COPERNICUS/S1_GRD")
        .filterBounds(selected_area)
        .filterDate(start_date, end_date_exclusive)
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
        .select(["VV", "VH"])
    )
    s1_count, s1_dates = get_collection_acquisition_metadata(s1_collection)

    if s1_count == 0:
        return {
            "image": None,
            "s2_count": s2_count,
            "s1_count": 0,
            "quality_metrics": quality_metrics,
            "quality_flag": "FAILED",
            "sentinel2_dates": s2_dates,
            "sentinel1_dates": [],
            "reason": "No Sentinel-1 VV/VH scenes for this period (independent of cloud threshold).",
        }

    s1_median = s1_collection.median().clip(selected_area)
    vv = s1_median.select("VV")
    vh = s1_median.select("VH")

    stacked = (
        s2_median.select(["B4", "B3", "B2"])
        .addBands(ndvi)
        .addBands(evi)
        .addBands(nbr)
        .addBands(s1_median.select(["VV", "VH"]))
        .addBands(vv.divide(vh).rename("VV_VH_ratio"))
        .addBands(vv.subtract(vh).rename("VV_minus_VH"))
        .select(FINAL_BAND_ORDER)
        .clip(selected_area)
        .toFloat()
    )

    quality_flag = compute_quality_flag(
        s2_count, s1_count, quality_metrics["average_cloud"], quality_metrics["missing_percentage"]
    )
    warnings = build_quality_warnings(
        f"{start_date}..{end_date_exclusive}", s2_count, s1_count, quality_metrics, quality_flag
    )

    return {
        "image": stacked,
        "s2_count": s2_count,
        "s1_count": s1_count,
        "quality_metrics": quality_metrics,
        "quality_flag": quality_flag,
        "sentinel2_dates": s2_dates,
        "sentinel1_dates": s1_dates,
        "warnings": warnings,
    }


def build_year_composite_with_retry(
    selected_area,
    start_date: str,
    end_date: str,
    cloud_thresholds: Optional[list[float]] = None,
) -> dict[str, Any]:
    """Bounded cloud-threshold retry ladder: strictest threshold first, only
    escalating when the result is missing or WEAK."""
    ladder = list(cloud_thresholds or DEFAULT_CLOUD_THRESHOLD_LADDER)[:MAX_RETRY_ATTEMPTS]
    if not ladder:
        ladder = [DEFAULT_CLOUD_THRESHOLD_LADDER[0]]

    # filterDate's end is exclusive; add a day to include end_date.
    end_date_exclusive = (datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

    attempts = []
    best_result = None
    best_attempt = None
    for attempt_index, threshold in enumerate(ladder, start=1):
        result = _build_yearly_stack(selected_area, start_date, end_date_exclusive, threshold)
        attempt_record = {
            "attempt": attempt_index,
            "cloud_threshold": threshold,
            "s2_scene_count": result["s2_count"] if result else 0,
            "s1_scene_count": result.get("s1_count", 0) if result else 0,
            "quality_flag": result["quality_flag"] if result else "FAILED",
            "usable_pixel_percentage": (
                round(100.0 - result["quality_metrics"]["missing_percentage"], 2)
                if result and result.get("quality_metrics")
                else None
            ),
        }
        attempts.append(attempt_record)

        if result is None:
            continue

        best_result = result
        best_attempt = attempt_record
        if result["quality_flag"] in {"FAILED", "GOOD", "FAIR"}:
            # FAILED here means zero Sentinel-1 scenes -- raising the cloud
            # threshold cannot fix that, so stop.
            break

    return {
        "image": best_result["image"] if best_result else None,
        "quality_flag": best_result["quality_flag"] if best_result else "FAILED",
        "attempts": attempts,
        "sentinel2_scene_count": best_result["s2_count"] if best_result else 0,
        "sentinel1_scene_count": best_result.get("s1_count", 0) if best_result else 0,
        "cloud_threshold_used": best_attempt["cloud_threshold"] if best_attempt else None,
        "usable_pixel_percentage": best_attempt["usable_pixel_percentage"] if best_attempt else None,
        "warnings": best_result.get("warnings", []) if best_result else [],
        "sentinel2_dates": best_result.get("sentinel2_dates", []) if best_result else [],
        "sentinel1_dates": best_result.get("sentinel1_dates", []) if best_result else [],
        "error": None if best_result and best_result["quality_flag"] != "FAILED" else (
            best_result.get("reason") if best_result else "No usable Sentinel-2 scenes found at any retry threshold."
        ),
    }


# ---------------------------------------------------------------------------
# GeoTIFF download (explicit grid, chunked, parallel, retried)
# ---------------------------------------------------------------------------

def compute_download_grid(coordinates: list) -> dict[str, Any]:
    """Pixel grid covering the AOI's bounding box, snapped to whole pixels."""
    lons = [point[0] for point in coordinates]
    lats = [point[1] for point in coordinates]
    d = PIXEL_SIZE_DEG
    west = math.floor(min(lons) / d) * d
    north = math.ceil(max(lats) / d) * d
    width = max(1, math.ceil((max(lons) - west) / d))
    height = max(1, math.ceil((north - min(lats)) / d))
    return {"west": west, "north": north, "pixel_size": d, "width": width, "height": height}


def _plan_chunks(grid: dict[str, Any]) -> list[tuple[int, int, int, int]]:
    """(col_off, row_off, width, height) chunks tiling the grid."""
    side = MAX_CHUNK_SIDE_PX
    chunks = []
    for row_off in range(0, grid["height"], side):
        for col_off in range(0, grid["width"], side):
            chunks.append((col_off, row_off,
                           min(side, grid["width"] - col_off),
                           min(side, grid["height"] - row_off)))
    return chunks


def _download_chunk(image, grid: dict[str, Any], chunk: tuple[int, int, int, int]) -> tuple[tuple, np.ndarray, Any]:
    import rasterio

    col_off, row_off, width, height = chunk
    d = grid["pixel_size"]
    x0 = grid["west"] + col_off * d
    y0 = grid["north"] - row_off * d
    last_error = None
    for attempt in range(1, DOWNLOAD_RETRIES + 1):
        try:
            url = image.getDownloadURL({
                "name": "chunk",
                "crs": "EPSG:4326",
                "crs_transform": [d, 0, x0, 0, -d, y0],
                "dimensions": f"{width}x{height}",
                "format": "GEO_TIFF",
                "filePerBand": False,
            })
            response = requests.get(url, timeout=300)
            response.raise_for_status()
            with rasterio.MemoryFile(BytesIO(response.content)) as memfile:
                with memfile.open() as src:
                    data = src.read().astype(np.float32)
                    nodata = src.nodata
            if data.shape != (len(FINAL_BAND_ORDER), height, width):
                raise RuntimeError(
                    f"Earth Engine returned a {data.shape} chunk, expected "
                    f"{(len(FINAL_BAND_ORDER), height, width)}."
                )
            return chunk, data, nodata
        except Exception as error:  # network / EE transient errors
            last_error = error
            if attempt < DOWNLOAD_RETRIES:
                time.sleep(2 * attempt)
    raise RuntimeError(f"GeoTIFF chunk at col {col_off}, row {row_off} failed after {DOWNLOAD_RETRIES} attempts: {last_error}")


def download_geotiff(image, coordinates: list, file_path: Path) -> dict[str, Any]:
    """Download `image` over the AOI's bounding box as one GeoTIFF on an
    explicit 10 m EPSG:4326 grid. Returns raster metadata."""
    import rasterio
    from rasterio.transform import Affine

    grid = compute_download_grid(coordinates)
    total_pixels = grid["width"] * grid["height"]
    if total_pixels > MAX_TOTAL_PIXELS:
        raise ValueError(
            f"Selected area is {grid['width']}x{grid['height']} pixels at 10 m "
            f"(~{total_pixels * BYTES_PER_PIXEL / 1e9:.1f} GB). Please select a smaller area "
            f"(limit {MAX_TOTAL_PIXELS:,} pixels)."
        )

    chunks = _plan_chunks(grid)
    stack = np.zeros((len(FINAL_BAND_ORDER), grid["height"], grid["width"]), dtype=np.float32)
    nodata_value = None
    with ThreadPoolExecutor(max_workers=min(DOWNLOAD_WORKERS, len(chunks))) as pool:
        for (col_off, row_off, width, height), data, nodata in pool.map(
            lambda chunk: _download_chunk(image, grid, chunk), chunks
        ):
            stack[:, row_off:row_off + height, col_off:col_off + width] = data
            if nodata is not None:
                nodata_value = nodata

    d = grid["pixel_size"]
    transform = Affine(d, 0, grid["west"], 0, -d, grid["north"])
    temp_path = file_path.with_suffix(".tif.part")
    profile = {
        "driver": "GTiff",
        "width": grid["width"],
        "height": grid["height"],
        "count": len(FINAL_BAND_ORDER),
        "dtype": "float32",
        "crs": "EPSG:4326",
        "transform": transform,
        "compress": "deflate",
        "predictor": 3,
        "tiled": grid["width"] >= 256 and grid["height"] >= 256,
    }
    if nodata_value is not None:
        profile["nodata"] = nodata_value
    with rasterio.open(temp_path, "w", **profile) as dst:
        dst.write(stack)
        for index, band_name in enumerate(FINAL_BAND_ORDER, start=1):
            dst.set_band_description(index, band_name)
    temp_path.replace(file_path)  # atomic: never leave a half-written .tif

    return {
        "width": grid["width"],
        "height": grid["height"],
        "crs": "EPSG:4326",
        "transform": list(transform)[:6],
        "bounds": [grid["west"], grid["north"] - grid["height"] * d,
                   grid["west"] + grid["width"] * d, grid["north"]],
        "chunk_count": len(chunks),
    }


# ---------------------------------------------------------------------------
# Job model
# ---------------------------------------------------------------------------

@dataclass
class YearRecord:
    year: int
    start_date: str
    end_date: str
    state: str = "QUEUED"
    quality_flag: Optional[str] = None
    attempts: list = field(default_factory=list)
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    drive_task_id: Optional[str] = None
    error: Optional[str] = None
    sentinel2_scene_count: int = 0
    sentinel1_scene_count: int = 0
    cloud_threshold_used: Optional[float] = None
    usable_pixel_percentage: Optional[float] = None
    raster_width: Optional[int] = None
    raster_height: Optional[int] = None
    raster_crs: Optional[str] = None
    raster_bounds: Optional[list] = None
    sentinel2_dates: list = field(default_factory=list)
    sentinel1_dates: list = field(default_factory=list)


def _default_labeling() -> dict[str, Any]:
    return {
        "year": None,
        "reference_ready": False,
        "reference_info": None,
        "labeling_reference_source": None,
        "screenshot_state": "QUEUED",
        "mask_saved": False,
        "error": None,
    }


@dataclass
class HistoricalJob:
    job_id: str
    area_name: str
    safe_area_name: str
    coordinates: list
    start_year: int
    end_year: int
    export_destination: str
    drive_folder: Optional[str]
    cloud_thresholds: list
    created_at: str
    years: dict = field(default_factory=dict)  # str(year) -> YearRecord
    job_status: str = "IDLE"  # IDLE | RUNNING | COMPLETED
    labeling: dict = field(default_factory=_default_labeling)
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False, compare=False)
    _active_threads: int = field(default=0, repr=False, compare=False)

    def directory(self) -> Path:
        path = DATASETS_DIR / self.job_id / self.safe_area_name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def metadata_path(self) -> Path:
        return DATASETS_DIR / self.job_id / "job.json"

    def zip_path(self) -> Path:
        return DATASETS_DIR / self.job_id / f"{self.safe_area_name}_{COLLECTION_YEAR}_Dataset.zip"

    def to_public_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "job_id": self.job_id,
                "area_name": self.area_name,
                "safe_area_name": self.safe_area_name,
                "coordinates": self.coordinates,
                "start_year": self.start_year,
                "end_year": self.end_year,
                "export_destination": self.export_destination,
                "drive_folder": self.drive_folder,
                "cloud_thresholds": self.cloud_thresholds,
                "job_status": self.job_status,
                "created_at": self.created_at,
                "years": {year: asdict(record) for year, record in self.years.items()},
                "labeling": json.loads(json.dumps(self.labeling)),
            }

    def save(self) -> None:
        with self._lock:
            DATASETS_DIR.joinpath(self.job_id).mkdir(parents=True, exist_ok=True)
            _atomic_write_text(self.metadata_path(), json.dumps(self.to_public_dict(), indent=2))
        _schedule_mirror(self.job_id)


def _atomic_write_text(path: Path, text: str) -> None:
    """Write via a temp file + rename. On Windows the rename can fail for a
    moment while another reader (mirror copy, antivirus, indexer) has the
    target open, so it is retried before falling back to a direct write."""
    temp_path = path.with_name(path.name + ".part")
    temp_path.write_text(text, encoding="utf-8")
    for attempt in range(20):
        try:
            temp_path.replace(path)
            return
        except PermissionError:
            time.sleep(0.05 * (attempt + 1))
    path.write_text(text, encoding="utf-8")
    temp_path.unlink(missing_ok=True)


_MIRROR_SKIP_SUFFIXES = {".zip", ".part"}
_mirror_pending: set[str] = set()
_mirror_condition = threading.Condition()


def _schedule_mirror(job_id: str) -> None:
    """Queue a mirror pass for this job. A single worker thread performs the
    copies, so mirroring never blocks (or races) the code that saves."""
    if EXTERNAL_MIRROR_DIR is None:
        return
    with _mirror_condition:
        _mirror_pending.add(job_id)
        _mirror_condition.notify()


def _mirror_worker() -> None:
    while True:
        with _mirror_condition:
            while not _mirror_pending:
                _mirror_condition.wait()
            job_id = _mirror_pending.pop()
        _mirror_job_directory(job_id)
        time.sleep(0.5)  # coalesce bursts of saves into fewer passes


threading.Thread(target=_mirror_worker, daemon=True, name="job-mirror").start()


def _mirror_job_directory(job_id: str) -> None:
    """Incrementally copy one job's folder to EXTERNAL_MIRROR_DIR: only files
    whose size or modification time changed are copied, and the dataset
    ZIP / temp files / backups are skipped. Failures never affect the real
    collection or labeling workflow."""
    if EXTERNAL_MIRROR_DIR is None:
        return
    source_dir = DATASETS_DIR / job_id
    if not source_dir.exists():
        return
    target_dir = EXTERNAL_MIRROR_DIR / job_id
    try:
        for source in source_dir.rglob("*"):
            if not source.is_file() or source.suffix in _MIRROR_SKIP_SUFFIXES or "backups" in source.parts:
                continue
            target = target_dir / source.relative_to(source_dir)
            stat = source.stat()
            if target.exists():
                target_stat = target.stat()
                if target_stat.st_size == stat.st_size and int(target_stat.st_mtime) == int(stat.st_mtime):
                    continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    except Exception as error:
        print(f"Mirror copy to {EXTERNAL_MIRROR_DIR} failed for job {job_id} (original data unaffected):", error)


def create_job(
    coordinates: list,
    area_name: str,
    export_destination: str = "local",
    drive_folder: Optional[str] = None,
    cloud_thresholds: Optional[list[float]] = None,
) -> HistoricalJob:
    validate_coordinates(coordinates)

    if not area_name or not str(area_name).strip():
        raise ValueError("Area name is required.")
    if export_destination not in {"local", "drive", "both"}:
        raise ValueError("export_destination must be local, drive, or both.")

    grid = compute_download_grid(coordinates)
    if grid["width"] * grid["height"] > MAX_TOTAL_PIXELS:
        raise ValueError(
            f"This area would be {grid['width']}x{grid['height']} pixels at 10 m, above this server's "
            f"limit of {MAX_TOTAL_PIXELS:,} pixels. Please draw a smaller area."
        )

    cleanup_old_jobs()
    period = collection_period()
    job = HistoricalJob(
        job_id=uuid.uuid4().hex,
        area_name=str(area_name).strip(),
        safe_area_name=sanitize_area_name(area_name),
        coordinates=coordinates,
        start_year=COLLECTION_YEAR,
        end_year=COLLECTION_YEAR,
        export_destination=export_destination,
        drive_folder=drive_folder,
        cloud_thresholds=list(cloud_thresholds or DEFAULT_CLOUD_THRESHOLD_LADDER),
        created_at=datetime.utcnow().isoformat() + "Z",
    )
    job.years[str(COLLECTION_YEAR)] = YearRecord(
        year=COLLECTION_YEAR, start_date=period["start_date"], end_date=period["end_date"]
    )

    with _JOBS_LOCK:
        JOBS[job.job_id] = job
    job.save()
    return job


def cleanup_old_jobs() -> int:
    """Delete finished jobs older than JOB_RETENTION_HOURS (no-op if unset)."""
    if JOB_RETENTION_HOURS <= 0:
        return 0
    cutoff = datetime.utcnow() - timedelta(hours=JOB_RETENTION_HOURS)
    removed = 0
    for job in list_jobs():
        try:
            created = datetime.fromisoformat(job.created_at.rstrip("Z"))
        except ValueError:
            continue
        if created >= cutoff or job._active_threads > 0:
            continue
        with _JOBS_LOCK:
            JOBS.pop(job.job_id, None)
        shutil.rmtree(DATASETS_DIR / job.job_id, ignore_errors=True)
        removed += 1
    if removed:
        print(f"Removed {removed} job(s) older than {JOB_RETENTION_HOURS:g} h.")
    return removed


def get_job(job_id: Optional[str]) -> Optional[HistoricalJob]:
    if not job_id:
        return None
    with _JOBS_LOCK:
        return JOBS.get(job_id)


def list_jobs() -> list[HistoricalJob]:
    with _JOBS_LOCK:
        jobs = list(JOBS.values())
    return sorted(jobs, key=lambda job: job.created_at, reverse=True)


def load_jobs_from_disk() -> int:
    """Reload every job.json under DATASETS_DIR (called once at startup).
    Work interrupted by a restart is marked FAILED so it can be retried."""
    record_fields = {f.name for f in fields(YearRecord)}
    loaded = 0
    for metadata_path in DATASETS_DIR.glob("*/job.json"):
        try:
            data = json.loads(metadata_path.read_text(encoding="utf-8"))
            years = {}
            for key, raw in (data.get("years") or {}).items():
                record = YearRecord(**{k: v for k, v in raw.items() if k in record_fields})
                if record.state in {"QUEUED", "PROCESSING", "EXPORTING", "RETRYING"}:
                    record.state = "FAILED"
                    record.error = "Interrupted by a server restart -- click Retry."
                years[key] = record
            labeling = _default_labeling()
            labeling.update(data.get("labeling") or {})
            if labeling.get("screenshot_state") in {"QUEUED", "PROCESSING"} and not labeling.get("reference_ready"):
                labeling["screenshot_state"] = "FAILED"
                labeling["error"] = "Interrupted by a server restart -- click Retry."
            job = HistoricalJob(
                job_id=data["job_id"],
                area_name=data["area_name"],
                safe_area_name=data.get("safe_area_name") or sanitize_area_name(data["area_name"]),
                coordinates=data.get("coordinates") or [],
                start_year=data.get("start_year") or COLLECTION_YEAR,
                end_year=data.get("end_year") or COLLECTION_YEAR,
                export_destination=data.get("export_destination") or "local",
                drive_folder=data.get("drive_folder"),
                cloud_thresholds=data.get("cloud_thresholds") or list(DEFAULT_CLOUD_THRESHOLD_LADDER),
                created_at=data.get("created_at") or "",
                years=years,
                job_status="COMPLETED" if data.get("job_status") == "RUNNING" else (data.get("job_status") or "IDLE"),
                labeling=labeling,
            )
            if not job.coordinates:
                continue  # very old job files without coordinates cannot be labeled
            with _JOBS_LOCK:
                JOBS[job.job_id] = job
            loaded += 1
        except Exception as error:
            print(f"Skipping unreadable job file {metadata_path}:", error)
    return loaded


# ---------------------------------------------------------------------------
# Background processing
# ---------------------------------------------------------------------------

def _selected_area_geometry(coordinates: list):
    return ee.Geometry.Polygon([close_polygon(coordinates)], proj=None, geodesic=False)


def _process_one_year(job: HistoricalJob, record: YearRecord) -> None:
    record.state = "PROCESSING"
    record.error = None
    job.save()

    selected_area = _selected_area_geometry(job.coordinates)
    try:
        result = build_year_composite_with_retry(
            selected_area, record.start_date, record.end_date, job.cloud_thresholds
        )
    except Exception as error:
        record.state = "FAILED"
        record.error = f"Earth Engine error: {error}"
        job.save()
        return

    record.attempts = result["attempts"]
    record.quality_flag = result["quality_flag"]
    record.sentinel2_scene_count = result["sentinel2_scene_count"]
    record.sentinel1_scene_count = result["sentinel1_scene_count"]
    record.cloud_threshold_used = result["cloud_threshold_used"]
    record.usable_pixel_percentage = result["usable_pixel_percentage"]
    record.sentinel2_dates = result["sentinel2_dates"]
    record.sentinel1_dates = result["sentinel1_dates"]

    if result["image"] is None or result["quality_flag"] == "FAILED":
        record.state = "FAILED"
        record.error = result["error"] or "No usable composite could be built for this year."
        job.save()
        return

    record.state = "EXPORTING"
    job.save()

    file_name = f"{scene_stem(job.safe_area_name, record.year)}.tif"
    file_path = job.directory() / file_name

    try:
        if job.export_destination in {"local", "both"}:
            raster = download_geotiff(result["image"], job.coordinates, file_path)
            record.file_name = file_name
            record.file_path = str(file_path)
            record.raster_width = raster["width"]
            record.raster_height = raster["height"]
            record.raster_crs = raster["crs"]
            record.raster_bounds = raster["bounds"]

        if job.export_destination in {"drive", "both"}:
            from services.export_service import export_to_google_drive

            drive_result = export_to_google_drive(
                result["image"], selected_area, folder_name=job.drive_folder or "February_2025_Dataset"
            )
            record.drive_task_id = drive_result["task_id"]

        record.state = "READY"
        record.error = None
    except Exception as error:
        record.state = "FAILED"
        record.error = f"Export failed: {error}"

    job.save()


def _capture_screenshot(job: HistoricalJob, force: bool = False) -> None:
    """Capture the high-resolution basemap screenshot for the AOI. Never
    raises: a failure is recorded on the job, and no invalid image is ever
    left on disk (see labeling_service.capture_basemap_reference)."""
    if job.labeling.get("reference_ready") and not force:
        return

    from services import labeling_service

    job.labeling["screenshot_state"] = "PROCESSING"
    job.labeling["error"] = None
    job.save()
    try:
        file_name = f"{scene_stem(job.safe_area_name, COLLECTION_YEAR)}_screenshot.png"
        reference_info = labeling_service.capture_basemap_reference(
            job.coordinates, job.directory() / file_name
        )
        job.labeling["reference_ready"] = True
        job.labeling["reference_info"] = reference_info
        job.labeling["screenshot_state"] = "READY"
        job.labeling["labeling_reference_source"] = (
            f"Esri World Imagery basemap (zoom {reference_info['zoom']}, "
            f"~{reference_info['ground_resolution_m']:.2f} m/pixel) -- the same satellite layer shown "
            "on the area-selection map. Not date-matched to February 2025."
        )
    except Exception as error:
        job.labeling["reference_ready"] = False
        job.labeling["screenshot_state"] = "FAILED"
        job.labeling["error"] = f"Screenshot capture failed: {error}"
        print(f"Screenshot capture failed for job {job.job_id}:", error)
    job.save()


def _run_years(job: HistoricalJob, years: Optional[list[int]]) -> None:
    target_years = years or [int(key) for key in job.years.keys()]
    for year in sorted(target_years):
        record = job.years.get(str(year))
        if record is None or record.state in {"READY", "DOWNLOADED"}:
            continue
        _process_one_year(job, record)


def _run_in_background(job: HistoricalJob, target, *args) -> None:
    def runner():
        try:
            target(*args)
        except Exception as error:
            # Never leave a record stuck in a busy state: surface the error
            # so the user can Retry.
            print(f"Background task failed for job {job.job_id}:", repr(error))
            with job._lock:
                for record in job.years.values():
                    if record.state in {"PROCESSING", "EXPORTING", "RETRYING"}:
                        record.state = "FAILED"
                        record.error = f"Unexpected error: {error}"
                if job.labeling.get("screenshot_state") == "PROCESSING":
                    job.labeling["screenshot_state"] = "FAILED"
                    job.labeling["error"] = f"Unexpected error: {error}"
            try:
                job.save()
            except Exception as save_error:
                print("Could not save job after failure:", save_error)
        finally:
            with job._lock:
                job._active_threads -= 1
                finished = job._active_threads == 0
            if finished:
                job.job_status = "COMPLETED"
                job.save()

    with job._lock:
        job._active_threads += 1
        job.job_status = "RUNNING"
    threading.Thread(target=runner, daemon=True).start()


def start_job_async(job_id: str) -> None:
    """Start the GeoTIFF and the screenshot in parallel."""
    job = get_job(job_id)
    if job is None:
        return
    _run_in_background(job, _capture_screenshot, job)
    _run_in_background(job, _run_years, job, None)
    job.save()


def retry_year(job_id: str, year: int) -> None:
    job = get_job(job_id)
    if job is None:
        raise ValueError("Job not found.")
    record = job.years.get(str(year))
    if record is None:
        raise ValueError("Year not part of this job.")
    if record.state in {"PROCESSING", "EXPORTING", "RETRYING"}:
        raise ValueError("This GeoTIFF is already being processed.")
    record.state = "RETRYING"
    job.save()
    _run_in_background(job, _run_years, job, [year])


def retry_screenshot(job_id: str) -> None:
    job = get_job(job_id)
    if job is None:
        raise ValueError("Job not found.")
    if job.labeling.get("screenshot_state") == "PROCESSING":
        raise ValueError("The screenshot is already being captured.")
    _run_in_background(job, _capture_screenshot, job, True)


def retry_all_failed(job_id: str) -> dict[str, Any]:
    job = get_job(job_id)
    if job is None:
        raise ValueError("Job not found.")
    failed_years = [record.year for record in job.years.values() if record.state == "FAILED"]
    for year in failed_years:
        job.years[str(year)].state = "RETRYING"
    screenshot_retry = job.labeling.get("screenshot_state") == "FAILED"
    job.save()
    if failed_years:
        _run_in_background(job, _run_years, job, failed_years)
    if screenshot_retry:
        _run_in_background(job, _capture_screenshot, job, True)
    return {"years": failed_years, "screenshot": screenshot_retry}
