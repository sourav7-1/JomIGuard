"""Calibrate tree COUNTS on Reyad's 300 real, hand-counted Gazipur squares.

    python ai/train_counter.py

For each square (data/gazipur/squares/SQ-xxxx_Gazipur/*.tif, 10 bands):
  1. run the trained 10-band U-Net -> tree / shrub / grass fractions,
  2. add per-band mean + std,
  3. fit a ridge regression (numpy only) from those features to
     trees per hectare (total, small, big) and tree cover %.
Accuracy is measured with 5-fold cross-validation on squares the model
never saw, and compared to a "predict the average" baseline.

Output: models/tree_counter.json + models/counter_report.json
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import COUNTER_FILE, GAZIPUR_DIR, MODELS_DIR, area_features, segment  # noqa: E402

TARGETS = {  # name -> (csv column index, per-hectare?, log-transform?)
    "total_trees": (5, True, True),
    "big_tree_share": ("share", False, False),  # big / total; small = total - big
    "tree_cover_pct": (6, False, False),
}
ALPHAS = [0.1, 0.3, 1, 3, 10, 30, 100, 300]
FOLDS = 5
LOG_CAP = float(np.log1p(5000))  # max 5000 trees/ha


def load_rows():
    with open(GAZIPUR_DIR / "gazipur_counts.csv", encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        next(reader)  # header: Area ID, Year, Area (m2), Small, Big, Total, Tree Cover %
        rows = []
        for r in reader:
            tifs = sorted((GAZIPUR_DIR / "squares" / f"{r[0]}_Gazipur").glob("*.tif"))
            if tifs:
                rows.append({"id": r[0], "area_m2": float(r[2]), "vals": [None] + [float(x) for x in r[1:]], "tif": tifs[0]})
        return rows


def ridge_fit(X, y, alpha):
    n, d = X.shape
    A = X.T @ X + alpha * np.eye(d)
    coef = np.linalg.solve(A, X.T @ (y - y.mean()))
    return coef, float(y.mean())


def cv_predict(X, y, alpha, folds):
    pred = np.zeros_like(y)
    for k in range(FOLDS):
        tr, te = folds != k, folds == k
        mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-9
        coef, b = ridge_fit((X[tr] - mu) / sd, y[tr], alpha)
        pred[te] = ((X[te] - mu) / sd) @ coef + b
    return pred


def score(true, pred):
    ss_res = float(((true - pred) ** 2).sum())
    ss_tot = float(((true - true.mean()) ** 2).sum())
    return {"R2": round(1 - ss_res / ss_tot, 3), "MAE": round(float(np.abs(true - pred).mean()), 2)}


def main():
    rows = load_rows()
    print(f"{len(rows)} Gazipur squares with imagery + real counts")
    X = np.stack([area_features(segment(r["tif"])) for r in rows])
    folds = np.random.default_rng(0).permutation(len(rows)) % FOLDS
    mu, sd = X.mean(0), X.std(0) + 1e-9

    models, report = {}, {"squares": len(rows), "folds": FOLDS, "targets": {}}
    for name, (col, per_ha, log) in TARGETS.items():
        if col == "share":
            raw = np.array([r["vals"][4] / r["vals"][5] if r["vals"][5] > 0 else 0.0 for r in rows])
        else:
            raw = np.array([r["vals"][col] for r in rows])
        y = raw / np.array([r["area_m2"] for r in rows]) * 10_000 if per_ha else raw
        yt = np.log1p(y) if log else y
        best = None
        for a in ALPHAS:
            p = cv_predict(X, yt, a, folds)
            hi = 1.0 if name == "big_tree_share" else 100.0
            p = np.expm1(np.clip(p, 0, LOG_CAP)) if log else p.clip(0, None if per_ha else hi)
            s = score(y, p)
            if best is None or s["MAE"] < best[1]["MAE"]:
                best = (a, s, p)
        alpha, s, p = best
        baseline = score(y, np.full_like(y, y.mean()))
        # count-level error for the actual squares (density * area)
        if per_ha:
            areas = np.array([r["area_m2"] for r in rows]) / 10_000
            s_count = score(raw, p * areas)
        else:
            s_count = None
        coef, b = ridge_fit((X - mu) / sd, yt, alpha)
        models[name] = {"coef": coef.tolist(), "intercept": b, "log": log, "per_hectare": per_ha, "alpha": alpha}
        report["targets"][name] = {"cv": s, "cv_count_per_square": s_count, "baseline_mean": baseline,
                                   "alpha": alpha, "unit": "trees/ha" if per_ha else ("fraction" if name == "big_tree_share" else "%")}
        if name == "big_tree_share":
            tot = report["targets"]["total_trees"]["_pred"]
            true_big = np.array([r["vals"][4] for r in rows]); true_small = np.array([r["vals"][3] for r in rows])
            report["targets"]["big_trees_derived"] = {"cv_count_per_square": score(true_big, tot * p)}
            report["targets"]["small_trees_derived"] = {"cv_count_per_square": score(true_small, tot * (1 - p))}
            print(f"  derived counts: big MAE {score(true_big, tot * p)['MAE']:.1f} (baseline {score(true_big, np.full_like(true_big, true_big.mean()))['MAE']:.1f}), "
                  f"small MAE {score(true_small, tot * (1 - p))['MAE']:.1f} (baseline {score(true_small, np.full_like(true_small, true_small.mean()))['MAE']:.1f})")
        if name == "total_trees":
            report["targets"][name]["_pred"] = p * np.array([r["area_m2"] for r in rows]) / 10_000
        print(f"{name:15s} CV R2 {s['R2']:6.3f}  MAE {s['MAE']:8.2f} {'trees/ha' if per_ha else '%'}"
              f"   (baseline MAE {baseline['MAE']:.2f})"
              + (f"   per-square count MAE {s_count['MAE']:.1f}" if s_count else ""))

    report["targets"]["total_trees"].pop("_pred", None)
    COUNTER_FILE.write_text(json.dumps({"feat_mean": mu.tolist(), "feat_std": sd.tolist(), "models": models}, indent=2))
    (MODELS_DIR / "counter_report.json").write_text(json.dumps(report, indent=2))
    print(f"Saved -> {COUNTER_FILE}")


if __name__ == "__main__":
    main()
