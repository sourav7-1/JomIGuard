"""Evaluate the document-type classifier (backend services/classify.py) on dataset v2.

Usage (Docker/Linux, from ml/, PYTHONPATH=../backend; needs Tesseract like eval.ocr_preview):
    python -m eval.classify_eval --split test       # v2 test split + all "other" images
    python -m eval.classify_eval --split train      # for tuning keywords (no "other" images)
Same as classify_image (gray -> OCR psm 3, psm 11 fallback -> classify_text), but OCR text is cached
per image under <out>/ocr/ so re-scoring after a keyword change is fast. Writes <out>/report.md
(report_<split>.md for other splits).
"""

import argparse
import csv
import hashlib
import json
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.services.classify import DOC_TYPES, PSM, classify_ocr
from app.services.ocr import ocr
from app.services.preprocess import preprocess

from eval.extraction import DATA, ML, PRESETS, load_items

CLASSES = (*DOC_TYPES, "other")


def ocr_text(png: Path, cache: Path, psm: int) -> str:
    data = png.read_bytes()
    suffix = "" if psm == PSM else f"_psm{psm}"
    hit = cache / f"{hashlib.sha256(data).hexdigest()}{suffix}.txt"
    if hit.exists():
        return hit.read_text(encoding="utf-8")
    text = ocr(preprocess(data).gray, psm=psm).text
    hit.write_text(text, encoding="utf-8", newline="\n")
    return text


def samples(split: str, dataset: str, data_root: Path, other_dir: Path | None) -> list[dict]:
    manifest = json.loads((ML / "datasets" / f"{dataset}.json").read_text(encoding="utf-8"))
    out = [
        {"id": it.image_id, "png": it.gt_path.with_suffix(".png"), "true": it.doc_type,
         "preset": it.preset}
        for it in load_items(manifest, data_root, split, None)
    ]  # fmt: skip
    if other_dir and (other_dir / "manifest.csv").exists():
        with (other_dir / "manifest.csv").open(encoding="utf-8") as f:
            out += [
                {"id": Path(r["output"]).stem, "png": other_dir / r["output"], "true": "other",
                 "preset": r["preset"]}
                for r in csv.DictReader(f)
            ]  # fmt: skip
    return out


def pct(n: int, d: int) -> str:
    return f"{100 * n / d:.1f}%" if d else "-"


def report(rows: list[dict], split: str) -> tuple[str, dict]:
    n = len(rows)
    ok = sum(r["true"] == r["pred"] for r in rows)
    confusion = Counter((r["true"], r["pred"]) for r in rows)
    off = [(c, pair) for pair, c in confusion.items() if pair[0] != pair[1]]
    worst = max(off) if off else None
    heavy = [r for r in rows if r["preset"] == "heavy"]
    lines = [
        f"# Document-type classifier: {split}",
        "",
        f'{n} images ({sum(r["true"] == "other" for r in rows)} "other"). '
        f"Accuracy **{pct(ok, n)}**.",
        "",
        "## Per class",
        "",
        "| class | images | precision | recall |",
        "|---|---|---|---|",
    ]
    for c in CLASSES:
        tp = confusion[(c, c)]
        predicted = sum(v for (_, p), v in confusion.items() if p == c)
        actual = sum(v for (t, _), v in confusion.items() if t == c)
        lines.append(f"| {c} | {actual} | {pct(tp, predicted)} | {pct(tp, actual)} |")
    lines += [
        "",
        "## Confusion matrix (rows: true, columns: predicted)",
        "",
        "| true \\ predicted | " + " | ".join(CLASSES) + " |",
        "|---" * (len(CLASSES) + 1) + "|",
    ]
    for t in CLASSES:
        lines.append(f"| {t} | " + " | ".join(str(confusion[(t, p)]) for p in CLASSES) + " |")
    lines += ["", "## By preset", "", "| preset | images | accuracy |", "|---|---|---|"]
    for p in PRESETS:
        sel = [r for r in rows if r["preset"] == p]
        lines.append(
            f"| {p} | {len(sel)} | {pct(sum(r['true'] == r['pred'] for r in sel), len(sel))} |"
        )
    mistakes = sorted((r for r in rows if r["true"] != r["pred"]), key=lambda r: r["confidence"])
    lines += [
        "",
        "## Lowest-confidence mistakes (up to 10)",
        "",
        "| image | preset | true | predicted | confidence | scores | matched keywords |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in mistakes[:10]:
        scores = ", ".join(f"{d} {s:g}" for d, s in r["scores"].items() if s)
        matched = "; ".join(f"{d}: {', '.join(k)}" for d, k in r["matched"].items() if k)
        lines.append(
            f"| {r['id']} | {r['preset']} | {r['true']} | {r['pred']} | {r['confidence']:.2f} "
            f"| {scores or '-'} | {matched or '-'} |"
        )
    summary = {
        "accuracy": ok / n if n else None,
        "worst_pair": (worst[1], worst[0]) if worst else None,
        "heavy_accuracy": (sum(r["true"] == r["pred"] for r in heavy) / len(heavy))
        if heavy
        else None,
        "mistakes": len(mistakes),
    }
    return "\n".join(lines) + "\n", summary


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--split", choices=["test", "train", "all"], default="test")
    ap.add_argument("--dataset", default="v2")
    ap.add_argument("--data-root", type=Path, default=DATA)
    ap.add_argument("--other-dir", type=Path, help="default: <data-root>/other (test split only)")
    ap.add_argument("--out", type=Path, help="default: <data-root>/eval/classify")
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 2)
    a = ap.parse_args()
    out = a.out or a.data_root / "eval" / "classify"
    cache = out / "ocr"
    cache.mkdir(parents=True, exist_ok=True)
    # "other" images are only for the final test: keyword tuning on train never sees them
    other = a.other_dir or (a.data_root / "other" if a.split == "test" else None)

    items = samples(a.split, a.dataset, a.data_root, other)
    with ThreadPoolExecutor(a.workers) as pool:  # Tesseract runs as a subprocess per call
        results = list(
            pool.map(lambda s: classify_ocr(lambda psm: ocr_text(s["png"], cache, psm)), items)
        )
    rows = []
    for s, res in zip(items, results, strict=True):
        rows.append({**s, "pred": res.doc_type, "confidence": res.confidence,
                     "scores": res.scores, "matched": res.matched_keywords})  # fmt: skip
    md, summary = report(rows, a.split)
    path = out / ("report.md" if a.split == "test" else f"report_{a.split}.md")
    path.write_text(md, encoding="utf-8", newline="\n")
    pair = summary["worst_pair"]
    heavy = summary["heavy_accuracy"]
    print(
        f"{a.split}: {len(rows)} images, accuracy {100 * summary['accuracy']:.1f}%, "
        f"mistakes {summary['mistakes']}, worst pair {pair[0][0]}->{pair[0][1]} x{pair[1]}"
        if pair
        else f"{a.split}: {len(rows)} images, accuracy {100 * summary['accuracy']:.1f}%"
    )
    if heavy is not None:
        print(f"heavy augmented: {100 * heavy:.1f}%")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
