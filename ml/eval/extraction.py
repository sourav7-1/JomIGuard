"""Extraction evaluation: field accuracy, precision/recall, critical-field accuracy and CER.

Usage (Docker like eval.ocr_preview, or Linux with PYTHONPATH=../backend), from ml/:
    python -m eval.extraction --pred <dir> --name <run> [--split test|train|all] [--doc-type deed]
    python -m eval.extraction --baseline oracle|empty [--name <run>]   # sanity baselines
    python -m eval.extraction compare <run_a> <run_b>
Predictions: <dir>/<image_id>.json, a valid ExtractedDocument or {"error": "..."}, with an
optional "meta": {latency_s, cost_usd, model}. Ground truth and split: ml/datasets/<dataset>.json.
Writes <out>/<run>/report.md, report.json and errors.csv (one row per wrong field).
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from eval.compare import (
    MODELS,
    Comparison,
    FieldResult,
    compare_documents,
    metrics,
    normalized,
    prepare_prediction,
)

ML = Path(__file__).resolve().parents[1]
DATA = ML.parent / "data"
DOC_ALIASES = {"mutation": "dcr"}
PRESETS = ("clean", "light", "medium", "heavy")
MAIN = ("accuracy", "precision", "recall", "critical_accuracy", "mean_cer", "list_count_accuracy")


@dataclass
class Item:
    image_id: str
    doc_type: str
    preset: str
    split: str | None
    gt_path: Path


def image_id(path: str) -> str:
    p = PurePosixPath(path)
    if p.parts[:2] == ("synthetic", "cases"):
        return f"{p.parts[2]}_{p.stem}"  # case_00001_deed
    return p.stem  # khatian_00001, case_00001_deed_0 (augmented)


def load_items(manifest: dict, data_root: Path, split: str, doc_type: str | None) -> list[Item]:
    presets = {}
    aug_csv = data_root / "augmented/manifest.csv"
    if aug_csv.exists():
        with aug_csv.open(encoding="utf-8") as f:
            presets = {PurePosixPath(r["output"]).stem: r["preset"] for r in csv.DictReader(f)}
    paths = {e["path"] for e in manifest["files"]}
    want = DOC_ALIASES.get(doc_type, doc_type)
    items = []
    for e in manifest["files"]:
        path = PurePosixPath(e["path"])
        gt = str(path.with_suffix(".json"))
        if path.suffix != ".png" or gt not in paths:
            continue
        if split != "all" and e.get("split") != split:
            continue
        gt_path = data_root / gt
        dt = json.loads(gt_path.read_text(encoding="utf-8"))["doc_type"]
        if want and dt != want:
            continue
        augmented = path.parts[0] == "augmented"
        preset = presets.get(path.stem, "unknown") if augmented else "clean"
        items.append(Item(image_id(e["path"]), dt, preset, e.get("split"), gt_path))
    return items


def ground_truth(item: Item) -> dict:
    model = MODELS[item.doc_type]
    return normalized(model.model_validate_json(item.gt_path.read_bytes()))


# prepared prediction: (normalized dict | None, error | None, meta)
Prepared = tuple[dict | None, str | None, dict]


def load_predictions(pred_dir: Path, items: list[Item]) -> dict[str, Prepared]:
    out = {}
    for it in items:
        f = pred_dir / f"{it.image_id}.json"
        raw = json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
        doc, err = prepare_prediction(raw)
        out[it.image_id] = (doc, err, (raw or {}).get("meta") or {})
    return out


def baseline(items: list[Item], kind: str) -> dict[str, Prepared]:
    """oracle: the ground truth itself (must score 100%). empty: only doc_type (near 0%)."""
    if kind == "oracle":
        return {it.image_id: (ground_truth(it), None, {}) for it in items}
    return {it.image_id: ({"doc_type": it.doc_type}, None, {}) for it in items}


def evaluate(items: list[Item], preds: dict[str, Prepared]) -> tuple[dict, list[dict]]:
    """-> (report, error rows)."""
    per_item: list[tuple[Item, Comparison]] = []
    missing = errors = 0
    meta_rows = []
    for it in items:
        doc, err, meta = preds.get(it.image_id, (None, "missing", {}))
        missing += err == "missing"
        errors += err is not None and err != "missing"
        per_item.append((it, compare_documents(ground_truth(it), doc)))
        if meta:
            meta_rows.append(meta)

    def group(keep) -> dict:
        sel = [c for it, c in per_item if keep(it)]
        return metrics([f for c in sel for f in c.fields], [lc for c in sel for lc in c.lists])

    by_field: dict[str, list[FieldResult]] = defaultdict(list)
    for _, c in per_item:
        for f in c.fields:
            by_field[f.generic].append(f)
    fields_table = []
    for generic, fs in by_field.items():
        m = metrics(fs)
        if m["fields_gt"] or m["fields_pred"] or m["mean_cer"] is not None:
            fields_table.append({"field": generic, "critical": fs[0].critical, **m})
    fields_table.sort(key=lambda r: (r["accuracy"] is None, r["accuracy"] or 0, r["field"]))

    def mean(key):
        vals = [m[key] for m in meta_rows if isinstance(m.get(key), int | float)]
        return sum(vals) / len(vals) if vals else None

    report = {
        "images": len(items),
        "missing_predictions": missing,
        "error_predictions": errors,
        "overall": group(lambda it: True),
        "by_doc_type": {d: group(lambda it, d=d: it.doc_type == d) for d in MODELS},
        "by_preset": {p: group(lambda it, p=p: it.preset == p) for p in PRESETS},
        "fields": fields_table,
        "mean_latency_s": mean("latency_s"),
        "mean_cost_usd": mean("cost_usd"),
        "models": sorted({str(m["model"]) for m in meta_rows if m.get("model")}),
    }
    rows = [
        {
            "image": it.image_id,
            "doc_type": it.doc_type,
            "preset": it.preset,
            "field_path": f.path,
            "expected": "" if f.expected is None else str(f.expected),
            "predicted": "" if f.predicted is None else str(f.predicted),
        }
        for it, c in per_item
        for f in c.fields
        if f.correct is False and (f.gt_present or f.pred_present)
    ]
    return report, rows


# --- output ---


def pct(v) -> str:
    return "-" if v is None else f"{100 * v:.1f}%"


def num(v, fmt=".3f") -> str:
    return "-" if v is None else format(v, fmt)


def metric_row(label: str, m: dict) -> str:
    return (
        f"| {label} | {m['critical_gt']} | {pct(m['accuracy'])} | {pct(m['precision'])} "
        f"| {pct(m['critical_accuracy'])} | {num(m['mean_cer'])} "
        f"| {pct(m['list_count_accuracy'])} |"
    )


def markdown(name: str, report: dict, args: dict) -> str:
    head = (
        "| group | critical fields | accuracy (= recall) | precision | critical accuracy "
        "| mean CER | list counts |\n|---|---|---|---|---|---|---|"
    )
    lines = [
        f"# Extraction eval: {name}",
        "",
        f"Dataset `{args['dataset']}`, split `{args['split']}`"
        + (f", doc type `{args['doc_type']}`" if args.get("doc_type") else "")
        + f". Images: {report['images']}; missing predictions: {report['missing_predictions']}; "
        f"error predictions: {report['error_predictions']}.",
        "",
        "Accuracy = correct / ground-truth fields (recall); precision = correct / predicted "
        "fields. Critical = rule identity, area, heirs or chain in fields.md (target >= 90%). "
        "CER covers *_text fields and printed names.",
        "",
        head,
        metric_row("**all**", report["overall"]),
    ]
    lines += [metric_row(d, m) for d, m in report["by_doc_type"].items() if m["fields_gt"]]
    lines += [metric_row(p, m) for p, m in report["by_preset"].items() if m["fields_gt"]]
    if report["mean_latency_s"] is not None or report["mean_cost_usd"] is not None:
        lines += [
            "",
            f"Mean latency: {num(report['mean_latency_s'], '.2f')} s; mean cost: "
            f"{num(report['mean_cost_usd'], '.5f')} USD; models: {', '.join(report['models'])}",
        ]
    lines += [
        "",
        "## Fields (worst first)",
        "",
        "| field | critical | gt | predicted | correct | accuracy | precision | mean CER |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in report["fields"]:
        lines.append(
            f"| {r['field']} | {'yes' if r['critical'] else ''} | {r['fields_gt']} "
            f"| {r['fields_pred']} | {r['fields_correct']} | {pct(r['accuracy'])} "
            f"| {pct(r['precision'])} | {num(r['mean_cer'])} |"
        )
    return "\n".join(lines) + "\n"


def write(out: Path, name: str, report: dict, rows: list[dict], args: dict) -> Path:
    run = out / name
    run.mkdir(parents=True, exist_ok=True)
    (run / "report.json").write_text(
        json.dumps({"name": name, "args": args, **report}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (run / "report.md").write_text(markdown(name, report, args), encoding="utf-8", newline="\n")
    with (run / "errors.csv").open("w", encoding="utf-8", newline="") as f:
        cols = ["image", "doc_type", "preset", "field_path", "expected", "predicted"]
        w = csv.DictWriter(f, cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return run


def compare_runs(out: Path, a: str, b: str) -> str:
    ra, rb = (json.loads((out / r / "report.json").read_text(encoding="utf-8")) for r in (a, b))
    lines = [f"| metric | {a} | {b} |", "|---|---|---|"]
    for key in MAIN:
        fmt = num if key == "mean_cer" else pct
        lines.append(f"| {key} | {fmt(ra['overall'][key])} | {fmt(rb['overall'][key])} |")
    for p in PRESETS:
        ca, cb = ra["by_preset"][p], rb["by_preset"][p]
        if ca["fields_gt"] or cb["fields_gt"]:
            lines.append(
                f"| critical_accuracy ({p}) | {pct(ca['critical_accuracy'])} "
                f"| {pct(cb['critical_accuracy'])} |"
            )
    for key in ("mean_latency_s", "mean_cost_usd"):
        lines.append(f"| {key} | {num(ra[key], '.4f')} | {num(rb[key], '.4f')} |")
    return "\n".join(lines)


def summary(report: dict) -> str:
    o = report["overall"]
    return (
        f"images {report['images']} (missing {report['missing_predictions']}, errors "
        f"{report['error_predictions']}): accuracy {pct(o['accuracy'])}, precision "
        f"{pct(o['precision'])}, critical {pct(o['critical_accuracy'])}, "
        f"mean CER {num(o['mean_cer'])}"
    )


def run_eval(
    dataset: str,
    data_root: Path,
    split: str,
    doc_type: str | None,
    preds_for,  # callable(items) -> dict[str, Prepared]
    name: str,
    out: Path,
) -> dict:
    manifest = json.loads((ML / "datasets" / f"{dataset}.json").read_text(encoding="utf-8"))
    items = load_items(manifest, data_root, split, doc_type)
    report, rows = evaluate(items, preds_for(items))
    args = {"dataset": dataset, "split": split, "doc_type": doc_type}
    write(out, name, report, rows, args)
    return report


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["compare"]:
        ap = argparse.ArgumentParser(prog="eval.extraction compare")
        ap.add_argument("run_a")
        ap.add_argument("run_b")
        ap.add_argument("--out", type=Path, default=DATA / "eval")
        a = ap.parse_args(argv[1:])
        print(compare_runs(a.out, a.run_a, a.run_b))
        return

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--pred", type=Path, help="folder of <image_id>.json predictions")
    src.add_argument("--baseline", choices=["oracle", "empty"])
    ap.add_argument("--name", help="run name (default: baseline_<kind> for baselines)")
    ap.add_argument("--split", choices=["test", "train", "all"], default="test")
    ap.add_argument("--doc-type", help="khatian, deed, mutation (dcr) or heir_cert")
    ap.add_argument("--dataset", default="v2", help="manifest ml/datasets/<dataset>.json")
    ap.add_argument("--data-root", type=Path, default=DATA)
    ap.add_argument("--out", type=Path, default=DATA / "eval")
    a = ap.parse_args(argv)
    name = a.name or (f"baseline_{a.baseline}" if a.baseline else None)
    if not name:
        ap.error("--name is required with --pred")

    def preds_for(items):
        return baseline(items, a.baseline) if a.baseline else load_predictions(a.pred, items)

    report = run_eval(a.dataset, a.data_root, a.split, a.doc_type, preds_for, name, a.out)
    print(f"{name}: {summary(report)}")
    print(f"wrote {a.out / name}")


if __name__ == "__main__":
    main()
