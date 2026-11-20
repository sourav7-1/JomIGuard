"""Monitor one area from the command line.

    python ai/predict.py path/to/area_S1_S2_Feb.tif
    python ai/predict.py path/to/area.tif --save-png out.png

Prints land-cover percentages, tree cover and the estimated tree count.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import analyse, class_colour_map, rgb_preview  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tif")
    ap.add_argument("--save-png", help="save RGB | class-map side by side")
    args = ap.parse_args()

    result = analyse(args.tif)
    seg = result.pop("_seg")
    print(json.dumps({k: v for k, v in result.items() if k != "classes"}, indent=2))
    print("\nLand cover:")
    for c in result["classes"]:
        if c["pixels"]:
            print(f"  {c['label']:18s} {c['percent']:6.2f}%  {c['area_m2']:>12,.0f} m2")

    if args.save_png:
        rgb = rgb_preview(seg["bands"], seg["valid"])
        cls = class_colour_map(seg["class_map"])
        Image.fromarray(np.concatenate([rgb, cls], 1)).save(args.save_png)
        print(f"\nSaved {args.save_png}")


if __name__ == "__main__":
    main()
