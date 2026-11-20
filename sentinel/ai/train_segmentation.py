"""Train the 10-band land-cover U-Net on the 50 human-labelled areas.

    python ai/train_segmentation.py            # default 150 epochs
    python ai/train_segmentation.py --epochs 60

Input : data/labelled/<area>/geotiff_model/<stem>.tif       (10 bands)
Label : data/labelled/<area>/geotiff_model/<stem>_mask.tif  (classes 0-9, 255 = ignore)
Output: models/segmentation_10band.pt + models/segmentation_report.json
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
import torch
from torch.utils.data import DataLoader, Dataset

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import (CLASSES, IGNORE, INPUT_SIZE, LABELLED_DIR, MODELS_DIR, NUM_BANDS, NUM_CLASSES,  # noqa: E402
                  SEG_CHECKPOINT, TREE_CLASS, SmallUNet, device, normalise, read_stack, resize_bands,
                  resize_mask)


def find_samples() -> list[dict]:
    samples = []
    for area in sorted(p for p in LABELLED_DIR.iterdir() if p.is_dir()):
        gdir = area / "geotiff_model"
        masks = sorted(gdir.glob("*_mask.tif"))
        if not masks:
            continue
        tif = gdir / masks[0].name.replace("_mask.tif", ".tif")
        if tif.exists():
            samples.append({"name": area.name, "tif": tif, "mask": masks[0]})
    return samples


def load_mask(path: Path, valid: np.ndarray) -> np.ndarray:
    with rasterio.open(str(path)) as src:
        m = src.read(1).astype(np.int64)
    m[~valid] = IGNORE
    m[(m < 0) | ((m >= NUM_CLASSES) & (m != IGNORE))] = IGNORE
    return m


def band_stats(samples: list[dict]) -> dict:
    """Per-band mean/std over all valid pixels of the TRAINING areas."""
    vals = [[] for _ in range(NUM_BANDS)]
    for s in samples:
        bands, valid = read_stack(s["tif"])
        for b in range(NUM_BANDS):
            vals[b].append(bands[b][valid])
    mean = [float(np.concatenate(v).mean()) for v in vals]
    std = [float(max(np.concatenate(v).std(), 1e-6)) for v in vals]
    return {"mean": mean, "std": std}


class LabelledAreas(Dataset):
    def __init__(self, samples, stats, augment: bool):
        self.items = []
        for s in samples:  # small dataset: keep everything in memory
            bands, valid = read_stack(s["tif"])
            x = resize_bands(normalise(bands, stats), INPUT_SIZE)
            y = resize_mask(load_mask(s["mask"], valid), INPUT_SIZE)
            self.items.append((x, y))
        self.augment = augment

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        x, y = self.items[i]
        if self.augment:  # flips / 90-degree rotations only (real reflectance values)
            if random.random() < 0.5:
                x, y = x[:, :, ::-1], y[:, ::-1]
            if random.random() < 0.5:
                x, y = x[:, ::-1, :], y[::-1, :]
            k = random.randint(0, 3)
            x, y = np.rot90(x, k, (1, 2)), np.rot90(y, k, (0, 1))
        return torch.from_numpy(x.copy()), torch.from_numpy(y.copy())


def class_weights(ds: LabelledAreas) -> torch.Tensor:
    counts = np.zeros(NUM_CLASSES, np.int64)
    for _, y in ds.items:
        v = y[y != IGNORE]
        counts += np.bincount(v, minlength=NUM_CLASSES)[:NUM_CLASSES]
    w = np.where(counts > 0, counts.sum() / (NUM_CLASSES * np.maximum(counts, 1)), 0.0)
    return torch.tensor(np.clip(w, 0, 20), dtype=torch.float32), counts


def confusion(model, ds) -> np.ndarray:
    cm = np.zeros((NUM_CLASSES, NUM_CLASSES), np.int64)
    model.eval()
    with torch.no_grad():
        for x, y in DataLoader(ds, batch_size=8):
            p = model(x.to(device())).argmax(1).cpu().numpy()
            y = y.numpy()
            k = y != IGNORE
            cm += np.bincount(y[k] * NUM_CLASSES + p[k], minlength=NUM_CLASSES ** 2).reshape(NUM_CLASSES, NUM_CLASSES)
    return cm


def metrics(cm: np.ndarray) -> dict:
    inter = np.diag(cm)
    union = cm.sum(0) + cm.sum(1) - inter
    present = cm.sum(1) > 0
    iou = np.where(union > 0, inter / np.maximum(union, 1), np.nan)
    return {
        "pixel_accuracy": float(inter.sum() / max(cm.sum(), 1)),
        "mIoU": float(np.nanmean(iou[present])) if present.any() else float("nan"),
        "tree_IoU": None if np.isnan(iou[TREE_CLASS]) else float(iou[TREE_CLASS]),
        "per_class_IoU": {CLASSES[c]["key"]: (None if np.isnan(iou[c]) else round(float(iou[c]), 4))
                          for c in range(NUM_CLASSES)},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=150)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--val-fraction", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed)
    samples = find_samples()
    rng = random.Random(args.seed)
    order = samples[:]
    rng.shuffle(order)
    n_val = max(1, round(len(order) * args.val_fraction))
    val_s, train_s = order[:n_val], order[n_val:]
    print(f"Device {device()} | {len(samples)} labelled areas -> train {len(train_s)}, val {len(val_s)}")

    stats = band_stats(train_s)
    train_ds, val_ds = LabelledAreas(train_s, stats, True), LabelledAreas(val_s, stats, False)
    weights, counts = class_weights(train_ds)
    print("Training pixels per class:", {CLASSES[c]["key"]: int(counts[c]) for c in range(NUM_CLASSES)})

    model = SmallUNet().to(device())
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs)
    loss_fn = torch.nn.CrossEntropyLoss(weight=weights.to(device()), ignore_index=IGNORE)
    loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True)

    best, history, t0 = -1.0, [], time.time()
    for epoch in range(1, args.epochs + 1):
        model.train()
        total = 0.0
        for x, y in loader:
            x, y = x.to(device()), y.to(device())
            opt.zero_grad()
            loss = loss_fn(model(x), y)
            loss.backward()
            opt.step()
            total += loss.item() * x.size(0)
        sched.step()
        m = metrics(confusion(model, val_ds))
        history.append({"epoch": epoch, "train_loss": total / len(train_ds), **{k: m[k] for k in ("pixel_accuracy", "mIoU", "tree_IoU")}})
        if epoch % 10 == 0 or epoch == 1:
            print(f"epoch {epoch:3d}  loss {total / len(train_ds):.4f}  val acc {m['pixel_accuracy']:.3f}  "
                  f"mIoU {m['mIoU']:.3f}  tree IoU {m['tree_IoU'] or 0:.3f}")
        score = m["mIoU"]
        if score > best:
            best = score
            torch.save({"model_state": model.state_dict(), "band_stats": stats, "band_names": None,
                        "epoch": epoch, "val": m, "train_areas": [s["name"] for s in train_s],
                        "val_areas": [s["name"] for s in val_s]}, SEG_CHECKPOINT)

    ckpt = torch.load(SEG_CHECKPOINT, map_location=device(), weights_only=False)
    report = {"best_epoch": ckpt["epoch"], "validation": ckpt["val"], "train_areas": ckpt["train_areas"],
              "val_areas": ckpt["val_areas"], "epochs": args.epochs, "seconds": round(time.time() - t0),
              "history": history}
    (MODELS_DIR / "segmentation_report.json").write_text(json.dumps(report, indent=2))
    v = ckpt["val"]
    print(f"\nBest epoch {ckpt['epoch']}: val pixel acc {v['pixel_accuracy']:.3f}, mIoU {v['mIoU']:.3f}, "
          f"tree IoU {v['tree_IoU'] or 0:.3f}  -> {SEG_CHECKPOINT}")


if __name__ == "__main__":
    main()
