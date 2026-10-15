"""Before/after preview of app.services.preprocess on augmented images.

Usage (from ml/):
    PYTHONPATH=../backend uv run python -m eval.preprocess_preview --n 12 --seed 1
Writes original | gray | binary strips with preset and meta to data/preview/preprocess/.
"""

import argparse
import csv
import random
from pathlib import Path

import cv2
import numpy as np
from app.services.preprocess import preprocess

DATA = Path(__file__).resolve().parents[2] / "data"
PANEL_H = 700


def pick(rows: list[dict], n: int, seed: int) -> list[dict]:
    """Spread n picks evenly over the presets (light/medium/heavy), at random within each."""
    rng = random.Random(seed)
    by_preset: dict[str, list[dict]] = {}
    for r in rows:
        by_preset.setdefault(r["preset"], []).append(r)
    presets = sorted(by_preset)
    picks = []
    for i, preset in enumerate(presets):
        k = n // len(presets) + (1 if i < n % len(presets) else 0)
        picks += rng.sample(by_preset[preset], min(k, len(by_preset[preset])))
    return picks


def panel(img: np.ndarray) -> np.ndarray:
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    scale = PANEL_H / img.shape[0]
    return cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)


def strip(original: np.ndarray, gray: np.ndarray, binary: np.ndarray, lines: list[str]):
    row = np.hstack([panel(original), panel(gray), panel(binary)])
    text = np.full((28 * len(lines) + 12, row.shape[1], 3), 255, np.uint8)
    for i, line in enumerate(lines):
        cv2.putText(text, line, (10, 28 * (i + 1)), cv2.FONT_HERSHEY_SIMPLEX, 0.65, 0, 1)
    return np.vstack([row, text])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--src", type=Path, default=DATA / "augmented")
    ap.add_argument("--out", type=Path, default=DATA / "preview" / "preprocess")
    args = ap.parse_args()

    with (args.src / "manifest.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    args.out.mkdir(parents=True, exist_ok=True)
    no_page = 0
    for i, row in enumerate(pick(rows, args.n, args.seed), 1):
        data = (args.src / row["output"]).read_bytes()
        res = preprocess(data)
        m = res.meta
        no_page += not m["page_found"]
        original = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        lines = [
            f"{row['output']}  preset={row['preset']}  angle={row['angle']}  "
            f"blur={row['blur']}  jpeg={row['jpeg_quality']}",
            f"page_found={m['page_found']}  deskew={m['deskew_angle']}  "
            f"{m['working_size']} -> {m['output_size']}  steps={','.join(m['steps'][1:])}",
            "warnings: " + ("; ".join(m["warnings"]) or "none"),
        ]
        name = f"{i:02d}_{row['preset']}_{Path(row['output']).stem}.png"
        cv2.imwrite(str(args.out / name), strip(original, res.gray, res.binary, lines))
        print(f"{name}: page_found={m['page_found']} deskew={m['deskew_angle']}")
    print(f"page_found False: {no_page} of {args.n}; wrote {args.out}")


if __name__ == "__main__":
    main()
