"""Shared AI code: 10-band Sentinel-1/2 reading, normalisation, the U-Net,
and inference. Used by the trainers, the web app and the command line.

Input bands (same order the collector writes):
    B4, B3, B2, NDVI, EVI, NBR, VV, VH, VV_VH_ratio, VV_minus_VH
No-data pixels are stored as -inf (or NaN) and are treated as invalid.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
import torch
import torch.nn as nn
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
LABELLED_DIR = DATA_DIR / "labelled"
GAZIPUR_DIR = DATA_DIR / "gazipur"
MODELS_DIR = ROOT / "models"
MODELS_DIR.mkdir(exist_ok=True)

SEG_CHECKPOINT = MODELS_DIR / "segmentation_10band.pt"
COUNTER_FILE = MODELS_DIR / "tree_counter.json"

BAND_NAMES = ["B4", "B3", "B2", "NDVI", "EVI", "NBR", "VV", "VH", "VV_VH_ratio", "VV_minus_VH"]
NUM_BANDS = 10
NUM_CLASSES = 10
IGNORE = 255
INPUT_SIZE = 256  # every image is resized to this for the network

CLASSES = [
    {"id": 0, "key": "water", "label": "Water", "color": "#2775CA"},
    {"id": 1, "key": "forest_tree", "label": "Forest / Tree", "color": "#1E7A34"},
    {"id": 2, "key": "grass_crop", "label": "Grass / Crop", "color": "#8BCA52"},
    {"id": 3, "key": "bare_mud_soil", "label": "Bare / Mud / Soil", "color": "#C2973F"},
    {"id": 4, "key": "sand", "label": "Sand", "color": "#E8D9A0"},
    {"id": 5, "key": "building", "label": "Building", "color": "#D62728"},
    {"id": 6, "key": "road", "label": "Road", "color": "#808080"},
    {"id": 7, "key": "shrub", "label": "Shrub", "color": "#7A7A2E"},
    {"id": 8, "key": "shadow", "label": "Shadow", "color": "#3D3D3D"},
    {"id": 9, "key": "unknown", "label": "Unknown / Other", "color": "#FFFFFF"},
]
TREE_CLASS = 1
SHRUB_CLASS = 7


# ---------------------------------------------------------------------------
# Reading + normalisation
# ---------------------------------------------------------------------------

def read_stack(tif_path: str | Path) -> tuple[np.ndarray, np.ndarray]:
    """Return (bands float32 (10,H,W) with invalid -> NaN, valid mask (H,W))."""
    with rasterio.open(str(tif_path)) as src:
        if src.count != NUM_BANDS:
            raise ValueError(f"Expected a 10-band Sentinel GeoTIFF, got {src.count} band(s).")
        bands = src.read().astype(np.float32)
    bands[~np.isfinite(bands)] = np.nan
    valid = np.all(np.isfinite(bands), axis=0)
    return bands, valid


def normalise(bands: np.ndarray, stats: dict) -> np.ndarray:
    """Global per-band z-score (stats computed once from the training set),
    so a pixel means the same thing in every image. Invalid -> 0."""
    mean = np.asarray(stats["mean"], dtype=np.float32)[:, None, None]
    std = np.asarray(stats["std"], dtype=np.float32)[:, None, None]
    out = (bands - mean) / std
    out = np.clip(out, -6, 6)
    return np.nan_to_num(out, nan=0.0).astype(np.float32)


def resize_bands(x: np.ndarray, size: int) -> np.ndarray:
    t = torch.from_numpy(x)[None]
    return F.interpolate(t, size=(size, size), mode="bilinear", align_corners=False)[0].numpy()


def resize_mask(mask: np.ndarray, size: int) -> np.ndarray:
    t = torch.from_numpy(mask.astype(np.int64))[None, None].float()
    return F.interpolate(t, size=(size, size), mode="nearest")[0, 0].numpy().astype(np.int64)


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class DoubleConv(nn.Module):
    def __init__(self, in_ch: int, out_ch: int):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, padding=1), nn.BatchNorm2d(out_ch), nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1), nn.BatchNorm2d(out_ch), nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.block(x)


class SmallUNet(nn.Module):
    """4-level U-Net, base width 24 (~1.9M params): small on purpose for 50
    labelled areas."""

    def __init__(self, in_channels: int = NUM_BANDS, num_classes: int = NUM_CLASSES, base_width: int = 24):
        super().__init__()
        w = base_width
        self.enc1, self.enc2 = DoubleConv(in_channels, w), DoubleConv(w, w * 2)
        self.enc3, self.enc4 = DoubleConv(w * 2, w * 4), DoubleConv(w * 4, w * 8)
        self.pool = nn.MaxPool2d(2)
        self.bottleneck = DoubleConv(w * 8, w * 16)
        self.up4, self.dec4 = nn.ConvTranspose2d(w * 16, w * 8, 2, stride=2), DoubleConv(w * 16, w * 8)
        self.up3, self.dec3 = nn.ConvTranspose2d(w * 8, w * 4, 2, stride=2), DoubleConv(w * 8, w * 4)
        self.up2, self.dec2 = nn.ConvTranspose2d(w * 4, w * 2, 2, stride=2), DoubleConv(w * 4, w * 2)
        self.up1, self.dec1 = nn.ConvTranspose2d(w * 2, w, 2, stride=2), DoubleConv(w * 2, w)
        self.dropout = nn.Dropout2d(0.2)
        self.out_conv = nn.Conv2d(w, num_classes, 1)

    def forward(self, x):
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool(e1))
        e3 = self.enc3(self.pool(e2))
        e4 = self.enc4(self.pool(e3))
        b = self.dropout(self.bottleneck(self.pool(e4)))
        d4 = self.dec4(torch.cat([self.up4(b), e4], 1))
        d3 = self.dec3(torch.cat([self.up3(d4), e3], 1))
        d2 = self.dec2(torch.cat([self.up2(d3), e2], 1))
        d1 = self.dec1(torch.cat([self.up1(d2), e1], 1))
        return self.out_conv(d1)


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------

_cache: dict = {}


def device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def load_segmenter():
    if "seg" not in _cache:
        if not SEG_CHECKPOINT.exists():
            raise FileNotFoundError("No trained model yet - run: python ai/train_segmentation.py")
        ckpt = torch.load(SEG_CHECKPOINT, map_location=device(), weights_only=False)
        model = SmallUNet().to(device())
        model.load_state_dict(ckpt["model_state"])
        model.eval()
        _cache["seg"] = (model, ckpt["band_stats"], ckpt)
    return _cache["seg"]


def load_counter() -> dict | None:
    if "counter" not in _cache:
        _cache["counter"] = json.loads(COUNTER_FILE.read_text()) if COUNTER_FILE.exists() else None
    return _cache["counter"]


def reset_cache():
    _cache.clear()


@torch.no_grad()
def segment(tif_path: str | Path) -> dict:
    """Run the 10-band U-Net on one GeoTIFF. Returns the class map at the
    GeoTIFF's own resolution (255 where the pixel has no data), per-class
    probabilities' tree channel, and the raw bands."""
    model, stats, _ = load_segmenter()
    bands, valid = read_stack(tif_path)
    h, w = valid.shape
    x = resize_bands(normalise(bands, stats), INPUT_SIZE)
    logits = model(torch.from_numpy(x)[None].to(device()))
    logits = F.interpolate(logits, size=(h, w), mode="bilinear", align_corners=False)
    probs = torch.softmax(logits, 1)[0].cpu().numpy()
    class_map = probs.argmax(0).astype(np.uint8)
    class_map[~valid] = IGNORE
    return {"class_map": class_map, "probs": probs, "valid": valid, "bands": bands}


def pixel_area_m2(tif_path: str | Path) -> float:
    """Approximate ground area of one pixel (works for EPSG:4326 grids)."""
    with rasterio.open(str(tif_path)) as src:
        a, e = abs(src.transform.a), abs(src.transform.e)
        if src.crs and src.crs.is_geographic:
            lat = (src.bounds.top + src.bounds.bottom) / 2
            return (a * 111_320 * np.cos(np.radians(lat))) * (e * 110_574)
        return a * e


def area_features(seg: dict) -> np.ndarray:
    """Features describing one area, used by the tree counter:
    predicted tree / shrub / grass fractions + mean tree probability +
    mean and std of every band over valid pixels."""
    valid, cm, probs, bands = seg["valid"], seg["class_map"], seg["probs"], seg["bands"]
    n = max(int(valid.sum()), 1)
    f = [
        float((cm[valid] == TREE_CLASS).sum()) / n,
        float((cm[valid] == SHRUB_CLASS).sum()) / n,
        float((cm[valid] == 2).sum()) / n,
        float(probs[TREE_CLASS][valid].mean()) if valid.any() else 0.0,
    ]
    for b in range(NUM_BANDS):
        v = bands[b][valid]
        f += [float(v.mean()) if v.size else 0.0, float(v.std()) if v.size else 0.0]
    return np.asarray(f, dtype=np.float64)


def predict_counts(features: np.ndarray, area_m2: float) -> dict | None:
    """Apply the Gazipur-calibrated ridge model (trees per hectare)."""
    counter = load_counter()
    if counter is None:
        return None
    z = (features - np.asarray(counter["feat_mean"])) / np.asarray(counter["feat_std"])
    raw = {}
    for target, m in counter["models"].items():
        val = float(z @ np.asarray(m["coef"]) + m["intercept"])
        if m.get("log"):
            val = float(np.expm1(np.clip(val, 0, np.log1p(5000))))
        raw[target] = max(val, 0.0)
    per_ha = raw["total_trees"]
    total = per_ha * area_m2 / 10_000
    share = min(max(raw.get("big_tree_share", 0.5), 0.0), 1.0)
    return {
        "total_trees": int(round(total)),
        "big_trees": int(round(total * share)),
        "small_trees": int(round(total * (1 - share))),
        "trees_per_ha": round(per_ha, 1),
        "tree_cover_pct": round(min(raw["tree_cover_pct"], 100.0), 1),
    }


def analyse(tif_path: str | Path) -> dict:
    """Full monitoring result for one 10-band GeoTIFF."""
    seg = segment(tif_path)
    valid, cm = seg["valid"], seg["class_map"]
    px_area = pixel_area_m2(tif_path)
    n_valid = int(valid.sum())
    classes = []
    for c in CLASSES:
        n = int((cm[valid] == c["id"]).sum())
        classes.append({**c, "pixels": n, "percent": round(100 * n / max(n_valid, 1), 2),
                        "area_m2": round(n * px_area, 1)})
    area_m2 = n_valid * px_area
    counts = predict_counts(area_features(seg), area_m2)
    return {
        "width": int(valid.shape[1]), "height": int(valid.shape[0]),
        "valid_pixels": n_valid, "area_m2": round(area_m2, 1), "area_ha": round(area_m2 / 10_000, 3),
        "tree_cover_pct_segmentation": next(c["percent"] for c in classes if c["id"] == TREE_CLASS),
        "classes": classes, "counts": counts, "_seg": seg,
    }


# ---------------------------------------------------------------------------
# Images for the web page
# ---------------------------------------------------------------------------

def rgb_preview(bands: np.ndarray, valid: np.ndarray) -> np.ndarray:
    rgb = np.stack([bands[0], bands[1], bands[2]], -1)  # B4,B3,B2
    v = rgb[valid]
    if v.size:
        lo, hi = np.percentile(v, 2), np.percentile(v, 98)
        rgb = np.clip((rgb - lo) / max(hi - lo, 1e-6), 0, 1)
    rgb = np.nan_to_num(rgb)
    rgb[~valid] = 0
    return (rgb * 255).astype(np.uint8)


def class_colour_map(class_map: np.ndarray) -> np.ndarray:
    out = np.zeros((*class_map.shape, 3), np.uint8)
    for c in CLASSES:
        h = c["color"].lstrip("#")
        out[class_map == c["id"]] = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    return out
