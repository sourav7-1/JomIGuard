"""Turn clean synthetic document images into phone-photo-like copies; ground truth unchanged.

Usage (from ml/):
    uv run python -m synth.augment --per-source 2 --seed 44 --out ../data/augmented
"""

import argparse
import csv
import hashlib
import random
import shutil
from dataclasses import dataclass
from pathlib import Path

import albumentations as A
import cv2
import numpy as np

PRESET_WEIGHTS = {"light": 50, "medium": 35, "heavy": 15}
TRAIN_FRACTION = 0.8

# Ranges per preset. Even "heavy" must stay readable by a person: keep it conservative.
PRESETS = {
    "light": {
        "angle": 2.0,
        "perspective": (0.0, 0.008),
        "margin": (0.04, 0.08),
        "blur": ["none", "gaussian"],
        "sigma": (0.3, 0.6),
        "motion_kernel": 3,
        "defocus_radius": 1,
        "shadow_p": 0.2,
        "shadow": (0.15, 0.3),
        "illumination": (0.02, 0.08),
        "brightness": (-0.08, 0.05),
        "contrast": (-0.05, 0.05),
        "gamma": (92, 108),
        "warm": (0, 8),
        "downscale": (0.8, 0.95),
        "noise": (0.005, 0.015),
        "jpeg": (75, 85),
    },
    "medium": {
        "angle": 4.0,
        "perspective": (0.005, 0.015),
        "margin": (0.05, 0.1),
        "blur": ["gaussian", "motion"],
        "sigma": (0.5, 0.9),
        "motion_kernel": 3,
        "defocus_radius": 1,
        "shadow_p": 0.5,
        "shadow": (0.15, 0.3),
        "illumination": (0.05, 0.15),
        "brightness": (-0.15, 0.05),
        "contrast": (-0.1, 0.05),
        "gamma": (85, 115),
        "warm": (5, 18),
        "downscale": (0.65, 0.8),
        "noise": (0.01, 0.025),
        "jpeg": (60, 78),
    },
    "heavy": {
        "angle": 8.0,
        "perspective": (0.01, 0.025),
        "margin": (0.06, 0.12),
        "blur": ["gaussian", "motion", "defocus"],
        "sigma": (0.7, 1.0),
        "motion_kernel": 5,
        "defocus_radius": 1,
        "shadow_p": 0.8,
        "shadow": (0.25, 0.4),
        "illumination": (0.1, 0.2),
        "brightness": (-0.2, 0.0),
        "contrast": (-0.1, 0.0),
        "gamma": (80, 120),
        "warm": (10, 25),
        "downscale": (0.6, 0.7),
        "noise": (0.02, 0.035),
        "jpeg": (40, 60),
    },
}

# procedural backgrounds (RGB): wooden desks and cloth
BACKGROUNDS = {
    "desk": [(120, 84, 52), (150, 108, 70), (92, 64, 44), (176, 140, 100)],
    "cloth": [(70, 80, 95), (110, 112, 108), (60, 90, 70), (170, 160, 140), (40, 40, 48)],
}

PARAM_COLUMNS = [
    "background",
    "angle",
    "perspective",
    "blur",
    "blur_value",
    "shadow",
    "illumination",
    "brightness",
    "contrast",
    "gamma",
    "warm_shift",
    "downscale",
    "noise_std",
    "jpeg_quality",
]


@dataclass
class Source:
    source_id: str  # khatian_00001 or case_00001; the split is assigned per source_id
    doc: str  # khatian | deed
    png: Path


def derive_seed(*parts) -> int:
    return int.from_bytes(hashlib.sha256(":".join(map(str, parts)).encode()).digest()[:4], "big")


def split_for(seed: int, source_id: str) -> str:
    return "train" if derive_seed(seed, "split", source_id) / 2**32 < TRAIN_FRACTION else "test"


def find_sources(src: Path) -> list[Source]:
    standalone = [Source(p.stem, "khatian", p) for p in sorted((src / "khatian").glob("*.png"))]
    cases = [Source(p.parent.name, p.stem, p) for p in sorted((src / "cases").glob("*/*.png"))]
    return standalone + cases


# --- parameters ---


def sample_params(rng: random.Random, preset: str) -> dict:
    r = PRESETS[preset]

    def u(lo_hi, nd=3):
        return round(rng.uniform(*lo_hi), nd)

    blur = rng.choice(r["blur"])
    blur_value = {
        "none": None,
        "gaussian": u(r["sigma"], 2),
        "motion": r["motion_kernel"],
        "defocus": r["defocus_radius"],
    }[blur]
    kind = rng.choice(sorted(BACKGROUNDS))
    return {
        "background": f"{kind}:{rng.randrange(len(BACKGROUNDS[kind]))}",
        "angle": u((-r["angle"], r["angle"]), 2),
        "perspective": u(r["perspective"]),
        "margin": u(r["margin"]),
        "blur": blur,
        "blur_value": blur_value,
        "shadow": u(r["shadow"]) if rng.random() < r["shadow_p"] else None,
        "illumination": u(r["illumination"]),
        "brightness": u(r["brightness"]),
        "contrast": u(r["contrast"]),
        "gamma": round(rng.uniform(*r["gamma"])),
        "warm_shift": round(rng.uniform(*r["warm"])),
        "downscale": u(r["downscale"]),
        "noise_std": u(r["noise"], 4),
        "jpeg_quality": rng.randint(*r["jpeg"]),
    }


# --- geometry: page onto a procedural background ---


def background(params: dict, size: tuple[int, int], np_rng: np.random.Generator) -> np.ndarray:
    w, h = size
    kind, idx = params["background"].split(":")
    base = np.array(BACKGROUNDS[kind][int(idx)], dtype=np.float32)
    # low-frequency blotches + grain (stretched along x for wood)
    blotch = cv2.resize(np_rng.normal(0, 1, (8, 8)).astype(np.float32), (w, h))
    gh, gw = (h // 2, 16) if kind == "desk" else (h // 4, w // 4)
    grain = cv2.resize(np_rng.normal(0, 1, (gh, gw)).astype(np.float32), (w, h))
    texture = 10 * blotch + (14 if kind == "desk" else 6) * grain
    return np.clip(base + texture[..., None], 0, 255).astype(np.uint8)


def place_page(page: np.ndarray, params: dict, np_rng: np.random.Generator) -> np.ndarray:
    """Rotate + perspective-warp the page onto a larger textured background."""
    h, w = page.shape[:2]
    a = np.deg2rad(params["angle"])
    corners = np.array([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]])
    rot = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    jitter = np_rng.uniform(-1, 1, (4, 2)) * params["perspective"] * w
    dst = corners @ rot.T + jitter
    margin = params["margin"] * w
    dst -= dst.min(axis=0) - margin
    cw, ch = (np.ceil(dst.max(axis=0) + margin)).astype(int)

    src = np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype=np.float32)
    m = cv2.getPerspectiveTransform(src, dst.astype(np.float32))
    warped = cv2.warpPerspective(page, m, (cw, ch), flags=cv2.INTER_LINEAR)
    mask = cv2.warpPerspective(np.ones((h, w), np.float32), m, (cw, ch), flags=cv2.INTER_LINEAR)

    canvas = background(params, (cw, ch), np_rng).astype(np.float32)
    drop = cv2.GaussianBlur(np.roll(mask, (12, 8), axis=(0, 1)), (0, 0), 10)
    canvas *= 1 - 0.35 * drop[..., None]  # soft drop shadow under the page
    out = canvas * (1 - mask[..., None]) + warped.astype(np.float32) * mask[..., None]
    return np.clip(out, 0, 255).astype(np.uint8)


def soft_shadow(img: np.ndarray, intensity: float, np_rng: np.random.Generator) -> np.ndarray:
    """Soft-edged shadow (phone/arm) over part of the frame; A.RandomShadow is hard-edged."""
    h, w = img.shape[:2]
    theta = np_rng.uniform(0, 2 * np.pi)
    cx, cy = np_rng.uniform(0.25, 0.75) * w, np_rng.uniform(0.25, 0.75) * h  # edge passes here
    softness = np_rng.uniform(0.03, 0.08) * w
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dist = (xx - cx) * np.cos(theta) + (yy - cy) * np.sin(theta)
    mask = 1 / (1 + np.exp(-dist / softness))
    return np.clip(img * (1 - intensity * mask)[..., None], 0, 255).astype(np.uint8)


def warm_cast(img: np.ndarray, shift: int) -> np.ndarray:
    """Yellow/warm cast in pixel units. Not A.RGBShift: in 2.0.8 a shift in [-1, 1] is read as
    a fraction of 255, so a 1-pixel shift saturated the whole channel."""
    offset = np.array([shift, shift // 3, -shift], dtype=np.int16)
    return np.clip(img.astype(np.int16) + offset, 0, 255).astype(np.uint8)


# --- photometric: albumentations with fixed (already sampled) values ---


def photometric(params: dict) -> list:
    p = params
    ts = [
        A.Illumination(
            mode="linear", intensity_range=(p["illumination"],) * 2, effect_type="both", p=1
        ),
        A.RandomBrightnessContrast(
            brightness_limit=(p["brightness"],) * 2, contrast_limit=(p["contrast"],) * 2, p=1
        ),
        A.RandomGamma(gamma_limit=(p["gamma"],) * 2, p=1),
    ]
    if p["blur"] == "gaussian":
        ts.append(A.GaussianBlur(blur_limit=0, sigma_limit=(p["blur_value"],) * 2, p=1))
    elif p["blur"] == "motion":
        ts.append(A.MotionBlur(blur_limit=(p["blur_value"],) * 2, allow_shifted=False, p=1))
    elif p["blur"] == "defocus":
        ts.append(A.Defocus(radius=(p["blur_value"],) * 2, alias_blur=(0.1, 0.1), p=1))
    ts += [
        A.Downscale(
            scale_range=(p["downscale"],) * 2,
            interpolation_pair={"downscale": cv2.INTER_AREA, "upscale": cv2.INTER_LINEAR},
            p=1,
        ),
        A.GaussNoise(std_range=(p["noise_std"],) * 2, per_channel=False, p=1),
        A.ImageCompression(compression_type="jpeg", quality_range=(p["jpeg_quality"],) * 2, p=1),
    ]
    return ts


def augment_image(page_rgb: np.ndarray, preset: str, seed: int) -> tuple[np.ndarray, dict]:
    rng = random.Random(seed)
    params = sample_params(rng, preset)
    np_rng = np.random.default_rng(seed)
    photo = place_page(page_rgb, params, np_rng)
    if params["shadow"] is not None:
        photo = soft_shadow(photo, params["shadow"], np_rng)
    photo = warm_cast(photo, params["warm_shift"])
    photo = A.Compose(photometric(params), seed=seed)(image=photo)["image"]
    return photo, params


# --- I/O ---


def read_rgb(path: Path) -> np.ndarray:
    return cv2.cvtColor(cv2.imread(str(path), cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)


def write_rgb(path: Path, img: np.ndarray) -> None:
    cv2.imwrite(str(path), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))


def contact_sheet(rows: list[dict], out: Path, seed: int, n: int = 24, cols: int = 6) -> None:
    picks = random.Random(seed).sample(rows, min(n, len(rows)))
    tw, th, label = 300, 330, 34
    sheet = np.full(((th + label) * -(-len(picks) // cols), tw * cols, 3), 255, np.uint8)
    for i, row in enumerate(picks):
        img = cv2.imread(str(out / row["output"]))
        scale = min(tw / img.shape[1], th / img.shape[0])
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        y, x = (i // cols) * (th + label), (i % cols) * tw
        sheet[y : y + img.shape[0], x : x + img.shape[1]] = img
        text = f"{row['preset']}  {row['output'].removesuffix('.png')}"
        cv2.putText(sheet, text, (x + 4, y + th + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.42, 0, 1)
    cv2.imwrite(str(out / "contact_sheet.png"), sheet)


def generate(src: Path, out: Path, per_source: int, seed: int) -> list[dict]:
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for s in find_sources(src):
        page = read_rgb(s.png)
        for k in range(per_source):
            img_seed = derive_seed(seed, s.source_id, s.doc, k)
            preset = random.Random(img_seed).choices(
                list(PRESET_WEIGHTS), weights=list(PRESET_WEIGHTS.values())
            )[0]
            photo, params = augment_image(page, preset, img_seed)
            name = f"{s.source_id}_{s.doc}_{k}"
            write_rgb(out / f"{name}.png", photo)
            shutil.copyfile(s.png.with_suffix(".json"), out / f"{name}.json")
            rows.append(
                {
                    "output": f"{name}.png",
                    "source": s.png.relative_to(src).as_posix(),
                    "source_id": s.source_id,
                    "doc_type": s.doc,
                    "preset": preset,
                    "seed": img_seed,
                    "split": split_for(seed, s.source_id),
                    **{c: params[c] for c in PARAM_COLUMNS},
                }
            )

    with (out / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    contact_sheet(rows, out, seed)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", type=Path, default=Path("../data/synthetic"))
    ap.add_argument("--per-source", type=int, default=2)
    ap.add_argument("--seed", type=int, default=44)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    rows = generate(args.src, args.out, args.per_source, args.seed)
    print(f"wrote {len(rows)} images to {args.out}")


if __name__ == "__main__":
    main()
