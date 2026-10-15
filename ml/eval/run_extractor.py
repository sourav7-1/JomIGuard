"""Run an extractor on dataset images, write predictions, then evaluate them.

Usage (from ml/, Docker/Linux, PYTHONPATH=../backend; needs the backend's anthropic and
pydantic-settings packages in the environment):
    python -m eval.run_extractor --extractor llm --split test --limit 10 --name llm_haiku_v1
Predictions: <data-root>/predictions/<name>/<image_id>.json (document + "meta", or
{"error", "meta"}); report: <out>/<name>/ (see eval.extraction). Stops cleanly on
BudgetExceeded and evaluates the images done so far.
"""

import argparse
import json
import random
from dataclasses import asdict
from pathlib import Path

from app.services.extraction import BudgetExceeded

from eval.extraction import DATA, ML, evaluate, load_items, load_predictions, pct, summary, write

LIMIT_SEED = 0  # --limit takes a fixed random sample, so it mixes doc types and presets


def make_extractor(kind: str, model: str | None, image: str):
    if kind == "llm":
        from app.services.extraction.llm import AnthropicExtractor

        return AnthropicExtractor(model=model, image=image)
    if kind == "tesseract_regex":
        from app.services.extraction.tesseract_regex import TesseractRegexExtractor

        return TesseractRegexExtractor()
    raise ValueError(f"unknown extractor {kind!r}")


def prediction(result) -> dict:
    meta = asdict(result.meta)
    if result.document is None:
        return {"error": result.error, "meta": meta}
    return {**result.document.model_dump(mode="json", exclude_none=True), "meta": meta}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--extractor", choices=["llm", "tesseract_regex"], default="llm")
    ap.add_argument("--name", required=True)
    ap.add_argument("--split", choices=["test", "train", "all"], default="test")
    ap.add_argument("--doc-type")
    ap.add_argument("--limit", type=int, help="random sample of this many images (seed 0)")
    ap.add_argument("--model", help="override LLM_MODEL")
    ap.add_argument("--image", choices=["gray", "original"], default="gray")
    ap.add_argument("--dataset", default="v2")
    ap.add_argument("--data-root", type=Path, default=DATA)
    ap.add_argument("--out", type=Path, default=DATA / "eval")
    a = ap.parse_args()

    manifest = json.loads((ML / "datasets" / f"{a.dataset}.json").read_text(encoding="utf-8"))
    items = load_items(manifest, a.data_root, a.split, a.doc_type)
    if a.limit and a.limit < len(items):
        items = random.Random(LIMIT_SEED).sample(items, a.limit)
    extractor = make_extractor(a.extractor, a.model, a.image)
    pred_dir = a.data_root / "predictions" / a.name
    pred_dir.mkdir(parents=True, exist_ok=True)

    done = []
    for i, it in enumerate(items, 1):
        try:
            result = extractor.extract(it.gt_path.with_suffix(".png").read_bytes(), it.doc_type)
        except BudgetExceeded as e:
            print(f"stopped: {e}")
            break
        (pred_dir / f"{it.image_id}.json").write_text(
            json.dumps(prediction(result), ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        done.append(it)
        m = result.meta
        status = "ok" if result.document else f"error: {result.error}"
        print(f"[{i}/{len(items)}] {it.image_id}: {status} ({m.latency_s:.1f}s, "
              f"${m.cost_usd:.4f}{', cached' if m.cached else ''})")  # fmt: skip

    if not done:
        print("nothing to evaluate")
        return
    report, rows = evaluate(done, load_predictions(pred_dir, done))
    args = {"dataset": a.dataset, "split": a.split, "doc_type": a.doc_type,
            "extractor": a.extractor, "model": extractor.model, "image": a.image,
            "limit": a.limit, "evaluated": len(done), "requested": len(items)}  # fmt: skip
    write(a.out, a.name, report, rows, args)
    clean = report["by_preset"]["clean"]["critical_accuracy"]
    aug = [report["by_preset"][p] for p in ("light", "medium", "heavy")]
    aug_gt = sum(m["critical_gt"] for m in aug)
    aug_acc = (
        sum(m["critical_accuracy"] * m["critical_gt"] for m in aug if m["critical_gt"]) / aug_gt
        if aug_gt
        else None
    )
    print(f"{a.name}: {summary(report)}")
    print(f"critical accuracy: clean {pct(clean)}, augmented {pct(aug_acc)}")
    print(
        f"per document: {report['mean_latency_s'] or 0:.1f} s, ${report['mean_cost_usd'] or 0:.4f}"
    )
    if len(done) < len(items):
        print(f"INCOMPLETE: evaluated {len(done)} of {len(items)} images (budget)")
    print(f"wrote {a.out / a.name}")


if __name__ == "__main__":
    main()
