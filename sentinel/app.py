"""Sentinel Tree Monitor -- one small Flask app, three pages:

  /collect   draw an area -> 10-band Sentinel-1/2 GeoTIFF + basemap screenshot
  /labeling  draw land-cover polygons on the screenshot -> training masks
  /monitor   run the 10-band AI on any area -> land cover, tree cover, tree count

Run:  python app.py   ->  http://127.0.0.1:5060
"""
from datetime import datetime, timezone
import base64
import io
import json
import os
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from pathlib import Path

from flask import Flask, Response, jsonify, redirect, render_template, request, send_file

from services.earth_engine_service import initialize_earth_engine
from services import historical_collection_service as historical
from services import labeling_service as labeling
from services import label_stats

sys.path.insert(0, str(Path(__file__).resolve().parent / "ai"))
import core as ai  # noqa: E402

app = Flask(__name__)

# Earth Engine is only needed for NEW collections. If it can't connect, the
# monitor page (and labeling of already-collected areas) still works.
try:
    initialize_earth_engine()
    EE_READY, EE_ERROR = True, None
except Exception as ee_error:  # noqa: BLE001
    EE_READY, EE_ERROR = False, str(ee_error)
print(f"Loaded {historical.load_jobs_from_disk()} saved collection job(s) from disk.")


@app.route("/")
def home():
    return render_template("home.html", ee_ready=EE_READY, ee_error=EE_ERROR)


@app.route("/collect")
def collect_redirect():
    return redirect("/historical")


@app.route("/healthz")
def healthz():
    return jsonify({"ok": True})


WARN_OUTSIDE_VALID_FRACTION = 0.15


def _error(message, status=400, **extra):
    return jsonify({"success": False, "message": message, **extra}), status


def _job_or_404(job_id):
    job = historical.get_job(job_id)
    if job is None:
        return None, _error("Job not found.", 404)
    return job, None


def _screenshot_path(job):
    info = (job.labeling or {}).get("reference_info")
    if not info:
        return None
    path = labeling.screenshot_path_for(job.directory(), info)
    return path if path.exists() else None


# ---------------------------------------------------------------------------
# Historical / Manual Labeling pages
# ---------------------------------------------------------------------------

@app.route("/historical")
def historical_page():
    return render_template("historical.html", period=historical.collection_period())


@app.route("/labeling")
def labeling_page():
    return render_template("labeling.html")


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------

@app.route("/historical/config", methods=["GET"])
def historical_config():
    return jsonify({
        "success": True,
        "period": historical.collection_period(),
        "default_cloud_thresholds": historical.DEFAULT_CLOUD_THRESHOLD_LADDER,
        "label_classes": labeling.DEFAULT_LABEL_CLASSES,
        "max_total_pixels": historical.MAX_TOTAL_PIXELS,
        # Public OAuth client ID (not a secret) for "Save to Google Drive".
        # Not set in this project's .env, so the button stays inert.
        "google_client_id": os.environ.get("GOOGLE_OAUTH_CLIENT_ID", ""),
    })


@app.route("/historical/start", methods=["POST"])
def historical_start():
    data = request.get_json(silent=True)
    if not data:
        return _error("No data received.")
    if not data.get("coordinates"):
        return _error("Please draw an area on the map first.")
    try:
        # The collection year is fixed to 2025 server-side; any year sent by
        # an old client is ignored.
        job = historical.create_job(
            coordinates=data.get("coordinates"),
            area_name=data.get("area_name"),
            export_destination=data.get("export_destination", "local"),
            drive_folder=data.get("drive_folder"),
            cloud_thresholds=data.get("cloud_thresholds"),
        )
        historical.start_job_async(job.job_id)
        return jsonify({"success": True, "message": "Collection started.", "job": job.to_public_dict()})
    except ValueError as error:
        return _error(str(error))
    except Exception as error:
        print("Collection start error:", error)
        return _error("Could not start the collection.", 500, error=str(error))


@app.route("/historical/status/<job_id>", methods=["GET"])
def historical_status(job_id):
    job, error = _job_or_404(job_id)
    if error:
        return error
    return jsonify({"success": True, "job": job.to_public_dict()})


@app.route("/historical/jobs", methods=["GET"])
def historical_jobs():
    jobs = []
    for job in historical.list_jobs():
        ready_years = [int(y) for y, r in job.years.items() if r.state in {"READY", "DOWNLOADED"}]
        jobs.append({
            "job_id": job.job_id,
            "area_name": job.area_name,
            "created_at": job.created_at,
            "job_status": job.job_status,
            "years": sorted(int(y) for y in job.years),
            "ready_years": sorted(ready_years),
            "screenshot_ready": bool(job.labeling.get("reference_ready")),
            "mask_saved": bool(job.labeling.get("mask_saved")),
        })
    return jsonify({"success": True, "jobs": jobs})


@app.route("/historical/retry/<job_id>/<int:year>", methods=["POST"])
def historical_retry_year(job_id, year):
    try:
        historical.retry_year(job_id, year)
        return jsonify({"success": True, "message": f"Retrying the {year} GeoTIFF."})
    except ValueError as error:
        return _error(str(error))


@app.route("/historical/retry-screenshot/<job_id>", methods=["POST"])
def historical_retry_screenshot(job_id):
    try:
        historical.retry_screenshot(job_id)
        return jsonify({"success": True, "message": "Retrying the screenshot."})
    except ValueError as error:
        return _error(str(error))


@app.route("/historical/retry-all/<job_id>", methods=["POST"])
def historical_retry_all(job_id):
    try:
        result = historical.retry_all_failed(job_id)
        return jsonify({"success": True, **result})
    except ValueError as error:
        return _error(str(error))


@app.route("/historical/screenshot/<job_id>", methods=["GET"])
def historical_screenshot_download(job_id):
    job, error = _job_or_404(job_id)
    if error:
        return error
    path = _screenshot_path(job)
    if path is None:
        return _error(job.labeling.get("error") or "The screenshot is not ready yet.", 404)
    return send_file(str(path), mimetype="image/png", as_attachment=True, download_name=path.name, max_age=0)


# ---------------------------------------------------------------------------
# Labeling
# ---------------------------------------------------------------------------

@app.route("/labeling/select-year", methods=["POST"])
def labeling_select_year():
    """Return everything the labeling canvas needs for one job/year: the
    screenshot (default drawing surface), optional GeoTIFF-native previews,
    and any previously saved labels."""
    try:
        data = request.get_json(silent=True) or {}
        job, error = _job_or_404(data.get("job_id"))
        if error:
            return error
        year = str(data.get("year") or historical.COLLECTION_YEAR)

        record = job.years.get(year)
        tif_ready = bool(record and record.file_path and Path(record.file_path).exists())
        reference_info = job.labeling.get("reference_info")
        screenshot_ready = bool(job.labeling.get("reference_ready") and reference_info and _screenshot_path(job))

        if not screenshot_ready and not tif_ready:
            return _error(
                job.labeling.get("error") or "Neither the screenshot nor the GeoTIFF is ready yet -- wait for the "
                "collection to finish (or retry it on the collection page).",
            )

        response = {
            "success": True,
            "job": {"job_id": job.job_id, "area_name": job.area_name, "coordinates": job.coordinates},
            "year": int(year),
            "label_classes": labeling.DEFAULT_LABEL_CLASSES,
            "tif_ready": tif_ready,
            "screenshot_ready": screenshot_ready,
            "labeling": {k: v for k, v in job.labeling.items() if k not in {"previews"}},
        }
        if screenshot_ready:
            response["reference_url"] = f"/labeling/reference/{job.job_id}"
            response["reference_info"] = reference_info
            response["labeling_reference_source"] = job.labeling.get("labeling_reference_source")

        if tif_ready:
            import rasterio

            with rasterio.open(record.file_path) as src:
                response["geotiff"] = {
                    "file_name": record.file_name,
                    "width": src.width,
                    "height": src.height,
                    "crs": str(src.crs),
                    "transform": list(src.transform)[:6],
                }
            previews_by_year = job.labeling.setdefault("previews", {})
            preview_info = previews_by_year.get(year)
            if preview_info is None or not all(Path(p).exists() for p in preview_info.get("paths", {}).values()):
                try:
                    preview_info = labeling.generate_labeling_previews(
                        Path(record.file_path), job.coordinates, job.directory(), int(year)
                    )
                    previews_by_year[year] = preview_info
                    job.save()
                except Exception as preview_error:
                    preview_info = None
                    response["preview_error"] = f"Could not render GeoTIFF previews: {preview_error}"
            if preview_info is not None:
                response["preview_urls"] = {
                    mode: f"/labeling/preview/{job.job_id}/{year}/{mode}" for mode in preview_info["modes"]
                }
                response["preview_info"] = {k: v for k, v in preview_info.items() if k != "paths"}

        # Previously saved labels, converted to screenshot pixels so they can
        # be edited again on the canvas.
        saved = (job.labeling.get("outputs") or {}).get("labels_geojson")
        if saved and screenshot_ready and (job.directory() / saved).exists() and str(job.labeling.get("year")) == year:
            lonlat = labeling.read_labels_geojson(job.directory() / saved)
            response["saved_polygons"] = labeling.lonlat_polygons_to_screenshot_pixels(lonlat, reference_info)

        return jsonify(response)

    except Exception as error:
        print("Labeling select-year error:", error)
        return _error("Could not load this job for labeling.", 500, error=str(error))


@app.route("/labeling/reference/<job_id>", methods=["GET"])
def labeling_reference_image(job_id):
    job, error = _job_or_404(job_id)
    if error:
        return error
    path = _screenshot_path(job)
    if path is None:
        return _error(job.labeling.get("error") or "The screenshot has not been captured yet.", 404)
    return send_file(str(path), mimetype="image/png", max_age=0)


@app.route("/labeling/preview/<job_id>/<year>/<mode>", methods=["GET"])
def labeling_preview_image(job_id, year, mode):
    job, error = _job_or_404(job_id)
    if error:
        return error
    if mode not in labeling.PREVIEW_MODES:
        return _error("Unknown preview mode.")
    preview_info = (job.labeling.get("previews") or {}).get(str(year))
    preview_path = (preview_info or {}).get("paths", {}).get(mode)
    if not preview_path or not Path(preview_path).exists():
        return _error("Preview image is missing.", 404)
    return send_file(str(preview_path), mimetype="image/png", max_age=0)


@app.route("/labeling/save-mask", methods=["POST"])
def labeling_save_mask():
    """Save labels for BOTH training approaches from one set of polygons:

    * <stem>_labels.geojson        polygons in EPSG:4326 lon/lat (canonical)
    * <stem>_mask.png / _mask.tif  10-class mask on the GeoTIFF grid
    * <stem>_label.png             same, remapped to the 6-class U-Net scheme
    * <stem>_screenshot_mask.png   10-class mask on the screenshot grid
    * <stem>_screenshot_overlay.png colored check image

    Pixels outside the AOI (and, on the GeoTIFF grid, nodata pixels) are
    always 255 = ignore.
    """
    try:
        data = request.get_json(silent=True) or {}
        job, error = _job_or_404(data.get("job_id"))
        if error:
            return error
        year = str(data.get("year") or historical.COLLECTION_YEAR)
        polygons = data.get("polygons") or []
        confirm = bool(data.get("confirm_despite_warning"))
        reference_mode = data.get("reference_mode") or "screenshot"
        if reference_mode == "legacy":
            reference_mode = "screenshot"

        if not polygons:
            return _error("Draw at least one polygon before saving.")

        record = job.years.get(year)
        tif_path = Path(record.file_path) if record and record.file_path and Path(record.file_path).exists() else None
        reference_info = job.labeling.get("reference_info")
        screenshot_path = _screenshot_path(job)
        preview_info = (job.labeling.get("previews") or {}).get(year)

        if reference_mode == "screenshot" and not (reference_info and screenshot_path):
            return _error("The screenshot used for drawing is not available.")
        if reference_mode in labeling.PREVIEW_MODES and tif_path is None:
            return _error("The GeoTIFF used for drawing is not available.")

        lonlat_polygons = labeling.polygons_to_lonlat(polygons, reference_mode, reference_info, preview_info, tif_path)
        if not lonlat_polygons:
            return _error("None of the polygons were valid (each needs 3+ points and a known class).")

        stem = historical.scene_stem(job.safe_area_name, int(year))
        directory = job.directory()
        outputs, stats = {}, {}
        try:
            border_band_m = float(data.get("border_band_m", label_stats.DEFAULT_BORDER_BAND_M))
        except (TypeError, ValueError):
            border_band_m = label_stats.DEFAULT_BORDER_BAND_M
        border_band_m = max(0.0, min(border_band_m, label_stats.MAX_BORDER_BAND_M))
        fill_other = data.get("fill_unlabeled_as_other", True) is not False

        tif_mask = tif_allowed = None
        if tif_path is not None:
            tif_mask = labeling.rasterize_on_geotiff_grid(lonlat_polygons, tif_path)
            valid, aoi = labeling.compute_valid_and_aoi_masks(tif_path, job.coordinates)
            tif_allowed = valid & aoi
            tif_mask, stats["geotiff"] = labeling.enforce_valid_labels(tif_mask, tif_allowed)

        screenshot_mask = aoi_ss = None
        if reference_info and screenshot_path:
            screenshot_mask = labeling.rasterize_on_screenshot_grid(lonlat_polygons, reference_info)
            aoi_ss = labeling.aoi_mask_on_screenshot_grid(job.coordinates, reference_info)
            screenshot_mask, stats["screenshot"] = labeling.enforce_valid_labels(screenshot_mask, aoi_ss)

        worst = max((s["overridden_outside_valid_region_fraction"] for s in stats.values()), default=0.0)
        if worst > WARN_OUTSIDE_VALID_FRACTION and not confirm:
            return jsonify({
                "success": False,
                "warning": True,
                "stats": stats,
                "message": (
                    f"{worst * 100:.0f}% of the area you labeled is outside the selected polygon (or over "
                    "GeoTIFF no-data pixels). Those pixels will be saved as 255 = ignore, not as a class. "
                    "Save anyway?"
                ),
            }), 409

        labels_name = f"{stem}_labels.geojson"
        labeling.write_labels_geojson(lonlat_polygons, directory / labels_name, {
            "area_name": job.area_name,
            "job_id": job.job_id,
            "year": int(year),
            "aoi_lonlat": labeling.close_polygon_ring(job.coordinates),
            "drawn_on": reference_mode,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        })
        outputs["labels_geojson"] = labels_name

        # ---- Area statistics + border-uncertainty analysis ----
        import numpy as np
        import rasterio
        from PIL import Image

        screenshot_input = geotiff_input = None
        if screenshot_mask is not None:
            screenshot_input = {
                "mask": screenshot_mask, "aoi": aoi_ss, "reference_info": reference_info,
                "rgb": np.asarray(Image.open(screenshot_path).convert("RGB")),
            }
        if tif_mask is not None:
            with rasterio.open(tif_path) as src:
                geotiff_input = {"mask": tif_mask, "allowed": tif_allowed, "stack": src.read().astype(np.float32),
                                 "transform": src.transform, "crs": src.crs}
        area_stats, ss_band, tif_band = label_stats.compute(
            job.coordinates, border_band_m, screenshot=screenshot_input, geotiff=geotiff_input
        )
        area_stats["unlabeled_as_other"] = fill_other
        area_stats["other_class_id"] = label_stats.OTHER_CLASS_ID if fill_other else None
        geotiff_input = screenshot_input = None  # free the large arrays

        if tif_mask is not None:
            # 6-class mask from what was DRAWN: that scheme has no "other"
            # class, so the auto-filled rest stays 255 there.
            six_class = labeling.remap_to_six_class_mask(tif_mask)
            if fill_other:
                tif_mask = label_stats.fill_unlabeled_as_other(tif_mask, tif_allowed, tif_band)
            outputs["geotiff_mask_png"] = f"{stem}_mask.png"
            outputs["geotiff_mask_tif"] = f"{stem}_mask.tif"
            outputs["geotiff_label_6class_png"] = f"{stem}_label.png"
            labeling.save_label_png(tif_mask, directory / outputs["geotiff_mask_png"])
            labeling.save_label_geotiff(tif_mask, tif_path, directory / outputs["geotiff_mask_tif"])
            labeling.save_label_png(six_class, directory / outputs["geotiff_label_6class_png"])

        if screenshot_mask is not None:
            drawn_only = screenshot_mask
            if fill_other:
                screenshot_mask = label_stats.fill_unlabeled_as_other(screenshot_mask, aoi_ss, ss_band)
            outputs["screenshot_mask_png"] = f"{stem}_screenshot_mask.png"
            outputs["screenshot_overlay_png"] = f"{stem}_screenshot_overlay.png"
            labeling.save_label_png(screenshot_mask, directory / outputs["screenshot_mask_png"])
            labeling.copy_world_file(screenshot_path, directory / outputs["screenshot_mask_png"])
            # The check image shows what was drawn, not the auto-filled rest.
            labeling.save_color_overlay(screenshot_path, drawn_only, directory / outputs["screenshot_overlay_png"])

        outputs["label_stats_json"] = f"{stem}_label_stats.json"
        outputs["label_stats_csv"] = f"{stem}_label_stats.csv"
        labeling.backup_existing_file(directory / outputs["label_stats_json"])
        (directory / outputs["label_stats_json"]).write_text(json.dumps(area_stats, indent=2), encoding="utf-8")
        (directory / outputs["label_stats_csv"]).write_text(label_stats.to_csv(area_stats), encoding="utf-8")

        job.labeling.update({
            "year": int(year),
            "mask_saved": True,
            "method": "manual_drawing",
            "source": "user_manual_polygons",
            "drawn_on": reference_mode,
            "polygon_count": len(lonlat_polygons),
            "verified": True,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "outputs": outputs,
            "quality_stats": stats,
            "area_stats": area_stats,
            "border_band_m": border_band_m,
            "unlabeled_as_other": fill_other,
        })
        job.save()

        return jsonify({
            "success": True,
            "message": "Labels saved.",
            "polygon_count": len(lonlat_polygons),
            "outputs": outputs,
            "quality_stats": stats,
            "area_stats": area_stats,
            "geotiff_mask_saved": tif_mask is not None,
            "screenshot_mask_saved": screenshot_mask is not None,
        })

    except ValueError as error:
        return _error(str(error))
    except Exception as error:
        print("Save label mask error:", error)
        return _error("Could not save the labels.", 500, error=str(error))


# ---------------------------------------------------------------------------
# Dataset ZIP
# ---------------------------------------------------------------------------

DATASET_README = """February {year} dataset -- {area}

Two independent training layouts built from ONE set of polygons
(labels/*_labels.geojson, EPSG:4326 lon/lat):

geotiff_model/      Approach 1: model on the 10-band Sentinel-1/2 GeoTIFF
  <stem>.tif              input, bands: {bands}
  <stem>_mask.tif         10-class label, same CRS/transform as the input
  <stem>_mask.png         same label as PNG (same width x height as the .tif)
  <stem>_label.png        same label remapped to the 6-class U-Net scheme

screenshot_model/   Approach 2: model on the high-resolution basemap screenshot
  <stem>_screenshot.png   input (RGB, clean -- no text or outlines drawn on it)
  <stem>_screenshot_mask.png  10-class label, same width x height as the screenshot
  *.pgw / *.prj           world files (EPSG:3857) georeferencing both images
  <stem>_screenshot_overlay.png  labels blended over the screenshot (visual check only)

Label values: see classes.json. 255 = ignore (outside the selected polygon,
no-data, or the narrow uncertain border around labeled regions); exclude it
from the loss. If "unlabeled = Other" was on when saving, every other
unlabeled pixel inside the area is 9 (Unknown / other).

labels/<stem>_label_stats.json / .csv: total area (m2), area and % of each
class, the unlabeled rest, and the border analysis (certain / estimated /
maximum area per class).
Both images cover the same lon/lat rectangle; see metadata.json for exact bounds.
"""


def _dataset_entries(job):
    directory = job.directory()
    root = f"{job.safe_area_name}_{historical.COLLECTION_YEAR}_Dataset"
    outputs = job.labeling.get("outputs") or {}
    entries = []
    for record in job.years.values():
        if record.file_path and Path(record.file_path).exists():
            entries.append((Path(record.file_path), f"{root}/geotiff_model/{Path(record.file_path).name}"))
    for key in ("geotiff_mask_tif", "geotiff_mask_png", "geotiff_label_6class_png"):
        if outputs.get(key):
            entries.append((directory / outputs[key], f"{root}/geotiff_model/{outputs[key]}"))

    screenshot = _screenshot_path(job)
    if screenshot:
        for path in (screenshot, screenshot.with_suffix(".pgw"), screenshot.with_suffix(".prj")):
            entries.append((path, f"{root}/screenshot_model/{path.name}"))
    for key in ("screenshot_mask_png", "screenshot_overlay_png"):
        if outputs.get(key):
            path = directory / outputs[key]
            entries.append((path, f"{root}/screenshot_model/{path.name}"))
            if key == "screenshot_mask_png":
                for suffix in (".pgw", ".prj"):
                    entries.append((path.with_suffix(suffix), f"{root}/screenshot_model/{path.with_suffix(suffix).name}"))
    for key in ("labels_geojson", "label_stats_json", "label_stats_csv"):
        if outputs.get(key):
            entries.append((directory / outputs[key], f"{root}/labels/{outputs[key]}"))
    return root, entries


def _dataset_generated_files(job, root):
    """metadata.json / classes.json / README.txt, generated on the fly."""
    public = job.to_public_dict()
    metadata = {
        "area_name": job.area_name,
        "job_id": job.job_id,
        "aoi_lonlat": labeling.close_polygon_ring(job.coordinates),
        "collection_period": historical.collection_period(),
        "band_order": historical.FINAL_BAND_ORDER,
        "label_ignore_value": labeling.IGNORE_LABEL_VALUE,
        "screenshot": public["labeling"].get("reference_info"),
        "labeling": {k: v for k, v in public["labeling"].items() if k not in {"previews", "reference_info"}},
        "years": {
            year: {k: v for k, v in record.items() if k not in {"file_path", "attempts"}}
            for year, record in public["years"].items()
        },
        "created_at": job.created_at,
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    classes = {
        "ignore_value": labeling.IGNORE_LABEL_VALUE,
        "classes": labeling.DEFAULT_LABEL_CLASSES,
        "six_class_mapping": labeling.LABEL_TO_SIX_CLASS_MAP,
    }
    readme = DATASET_README.format(
        year=historical.COLLECTION_YEAR, area=job.area_name, bands=", ".join(historical.FINAL_BAND_ORDER)
    )
    return {
        f"{root}/metadata.json": json.dumps(metadata, indent=2, ensure_ascii=False),
        f"{root}/classes.json": json.dumps(classes, indent=2),
        f"{root}/README.txt": readme,
    }


def _mark_downloaded(job):
    for record in job.years.values():
        if record.state == "READY":
            record.state = "DOWNLOADED"
    job.save()


@app.route("/historical/download-zip/<job_id>", methods=["GET"])
def historical_download_zip(job_id):
    job, error = _job_or_404(job_id)
    if error:
        return error
    root, entries = _dataset_entries(job)
    if not entries:
        return _error("Nothing has been downloaded for this job yet.", 404)

    zip_path = labeling.build_dataset_zip(job.zip_path(), entries, _dataset_generated_files(job, root))
    _mark_downloaded(job)
    return send_file(str(zip_path), mimetype="application/zip", as_attachment=True,
                     download_name=f"{root}.zip", max_age=0)


@app.route("/historical/dataset-manifest/<job_id>", methods=["GET"])
def historical_dataset_manifest(job_id):
    """Every file of the dataset with its path inside the dataset folder --
    the same layout as the ZIP. Used by the browser to save the dataset into
    a Google Drive folder file by file."""
    job, error = _job_or_404(job_id)
    if error:
        return error
    root, entries = _dataset_entries(job)
    if not entries:
        return _error("Nothing has been downloaded for this job yet.", 404)
    generated = _dataset_generated_files(job, root)
    files = [{"path": arcname, "size": source.stat().st_size} for source, arcname in entries if source.exists()]
    files += [{"path": arcname, "size": len(text.encode("utf-8"))} for arcname, text in generated.items()]
    return jsonify({"success": True, "root": root, "files": files})


@app.route("/historical/dataset-file/<job_id>", methods=["GET"])
def historical_dataset_file(job_id):
    """One file of the dataset, addressed by its path from the manifest."""
    job, error = _job_or_404(job_id)
    if error:
        return error
    wanted = request.args.get("path", "")
    root, entries = _dataset_entries(job)
    for source, arcname in entries:
        if arcname == wanted and source.exists():
            return send_file(str(source), as_attachment=True, download_name=source.name, max_age=0)
    generated = _dataset_generated_files(job, root)
    if wanted in generated:
        return Response(generated[wanted], mimetype="application/json" if wanted.endswith(".json") else "text/plain")
    return _error("No such file in this dataset.", 404)


@app.route("/historical/mark-exported/<job_id>", methods=["POST"])
def historical_mark_exported(job_id):
    job, error = _job_or_404(job_id)
    if error:
        return error
    _mark_downloaded(job)
    return jsonify({"success": True})



# ---------------------------------------------------------------------------
# Monitoring (10-band AI)
# ---------------------------------------------------------------------------

def _png_b64(array):
    from PIL import Image

    img = Image.fromarray(array)
    scale = max(1, 360 // max(img.width, img.height))  # tiny tiles -> enlarge, keep pixels sharp
    if scale > 1:
        img = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _gazipur_rows():
    import csv

    path = ai.GAZIPUR_DIR / "gazipur_counts.csv"
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        next(reader)
        return {r[0]: {"id": r[0], "area_m2": float(r[2]), "small_trees": int(float(r[3])),
                       "big_trees": int(float(r[4])), "total_trees": int(float(r[5])),
                       "tree_cover_pct": float(r[6])} for r in reader}


def _model_info():
    info = {"segmentation_ready": ai.SEG_CHECKPOINT.exists(), "counter_ready": ai.COUNTER_FILE.exists()}
    for key, name in (("segmentation", "segmentation_report.json"), ("counter", "counter_report.json")):
        p = ai.MODELS_DIR / name
        if p.exists():
            rep = json.loads(p.read_text())
            rep.pop("history", None)
            rep.pop("train_areas", None)
            info[key] = rep
    return info


@app.route("/monitor")
def monitor_page():
    return render_template("monitor.html")


@app.route("/monitor/sources")
def monitor_sources():
    jobs = []
    for job in historical.list_jobs():
        for year, rec in job.years.items():
            if rec.file_path and Path(rec.file_path).exists():
                jobs.append({"job_id": job.job_id, "year": int(year), "area_name": job.area_name,
                             "created_at": job.created_at})
    gaz = sorted(_gazipur_rows().values(), key=lambda r: r["id"])
    labelled = sorted(p.name for p in ai.LABELLED_DIR.iterdir() if p.is_dir())
    return jsonify({"success": True, "jobs": jobs, "gazipur": gaz, "labelled": labelled, "models": _model_info()})


def _resolve_tif(data):
    if data.get("job_id"):
        job = historical.get_job(data["job_id"])
        if job is None:
            raise ValueError("Collection job not found.")
        rec = job.years.get(str(data.get("year") or historical.COLLECTION_YEAR))
        if not rec or not rec.file_path or not Path(rec.file_path).exists():
            raise ValueError("This job has no downloaded GeoTIFF yet.")
        return Path(rec.file_path), job.area_name, None
    if data.get("gazipur_id"):
        gid = str(data["gazipur_id"])
        tifs = sorted((ai.GAZIPUR_DIR / "squares" / f"{gid}_Gazipur").glob("*.tif"))
        if not tifs:
            raise ValueError("Gazipur square not found.")
        return tifs[0], f"{gid} (Gazipur)", _gazipur_rows().get(gid)
    if data.get("labelled"):
        folder = ai.LABELLED_DIR / Path(str(data["labelled"])).name
        tifs = [p for p in (folder / "geotiff_model").glob("*.tif") if not p.name.endswith("_mask.tif")]
        if not tifs:
            raise ValueError("Labelled area not found.")
        return tifs[0], folder.name, None
    raise ValueError("Choose an area to analyse.")


@app.route("/monitor/analyze", methods=["POST"])
def monitor_analyze():
    tmp = None
    try:
        if "file" in request.files:
            upload = request.files["file"]
            if not upload.filename.lower().endswith((".tif", ".tiff")):
                return _error("Upload a 10-band .tif GeoTIFF.")
            fd, tmp = tempfile.mkstemp(suffix=".tif")
            os.close(fd)
            upload.save(tmp)
            tif, name, truth = Path(tmp), upload.filename, None
        else:
            tif, name, truth = _resolve_tif(request.get_json(silent=True) or {})

        result = ai.analyse(tif)
        seg = result.pop("_seg")
        result["name"] = name
        result["ground_truth"] = truth
        result["rgb_png"] = _png_b64(ai.rgb_preview(seg["bands"], seg["valid"]))
        result["class_png"] = _png_b64(ai.class_colour_map(seg["class_map"]))
        return jsonify({"success": True, "result": result})
    except FileNotFoundError as error:
        return _error(str(error), 409)
    except ValueError as error:
        return _error(str(error))
    except Exception as error:  # noqa: BLE001
        print("Monitor error:", error)
        return _error("Could not analyse this area.", 500, error=str(error))
    finally:
        if tmp:
            try:
                os.remove(tmp)
            except OSError:
                pass

# ---------------------------------------------------------------------------
# JSON API for JomiGuard: multi-year satellite check of one plot
# ---------------------------------------------------------------------------

@app.route("/api/analyze-area", methods=["POST"])
def api_analyze_area():
    from services.area_analysis import analyze_area

    if not EE_READY:
        return _error("Earth Engine is not connected on this server.", 503, error=EE_ERROR)
    data = request.get_json(silent=True) or {}
    try:
        result = analyze_area(data.get("geometry"), data.get("years"), data.get("buffer_m", 200))
        return jsonify({"success": True, "result": result})
    except ValueError as error:
        return _error(str(error))
    except FileNotFoundError as error:  # model checkpoint missing
        return _error(str(error), 409)
    except Exception as error:  # noqa: BLE001
        print("analyze-area error:", error)
        return _error("Could not analyse this area.", 500, error=str(error))


@app.errorhandler(404)
def handle_not_found(error):
    if request.path.startswith(("/historical", "/labeling", "/monitor")) and request.method != "GET":
        return jsonify({"success": False, "message": "Requested route was not found."}), 404
    return render_template("home.html", ee_ready=EE_READY, ee_error=EE_ERROR), 404


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", use_reloader=False,
            host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 5060)))
