"""OCR preview: how many ground-truth values appear in Tesseract's text.

Usage: run in the backend image so Tesseract matches production (from the repo root):
    docker compose run --rm --no-deps -v ./ml:/ml -v ./data:/data -w /ml \
      -e PYTHONPATH=/app:/ml -e PYTHONIOENCODING=utf-8 --entrypoint /opt/venv/bin/python \
      backend -m eval.ocr_preview --n 20 --seed 1 --data-root /data
Picks n/2 clean case images and n/2 augmented images, runs preprocess -> OCR (psm 3, 4, 6),
and writes <data-root>/preview/ocr/{image}_psm{psm}.txt plus report.md.
--grid: psm 3 only; input (binary/gray) x scale (1x/2x) x lang x model (apt/best) -> grid.md.
"""

import argparse
import csv
import itertools
import json
import os
import random
import time
import unicodedata
from pathlib import Path

import cv2
from app.services.ocr import ocr, tesseract_version
from app.services.preprocess import preprocess
from rapidfuzz import fuzz

DATA = Path(__file__).resolve().parents[2] / "data"  # default --data-root
PSMS = (3, 4, 6)
ID_KEYS = {"khatian_no", "dag_no", "case_no", "deed_no"}
NAME_LISTS = {"owners", "sellers", "buyers", "heirs"}
FUZZY_MIN = 90
BOTH = ("ids", "names")
# model folders in the backend image (see backend/Dockerfile); selected via TESSDATA_PREFIX,
# same effect as --tessdata-dir (ocr() only passes --psm)
TESSDATA = {
    "apt": "/usr/share/tesseract-ocr/5/tessdata",
    "best": "/usr/share/tessdata_best",  # tessdata_best 4.1.0 ben + apt eng/osd
}
TO_BN = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def expected_values(gt) -> tuple[set[str], set[str]]:
    """(identifiers in Bangla digits, people's names as printed) from a ground-truth JSON."""
    ids, names = set(), set()

    def walk(node, key=None):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in ID_KEYS and isinstance(v, str):
                    ids.add(nfc(v.translate(TO_BN)))
                elif k in NAME_LISTS and isinstance(v, list):
                    names.update(nfc(p["name"]) for p in v if isinstance(p, dict) and "name" in p)
                walk(v, k)
        elif isinstance(node, list):
            for v in node:
                walk(v, key)

    walk(gt)
    return ids, names


def found(values: set[str], text: str) -> tuple[int, int]:
    """(exact matches, fuzzy matches: partial ratio >= FUZZY_MIN; exact counts as fuzzy)."""
    exact = sum(v in text for v in values)
    fuzzy = sum(v in text or fuzz.partial_ratio(v, text) >= FUZZY_MIN for v in values)
    return exact, fuzzy


def pick(n: int, seed: int, data: Path) -> list[dict]:
    """n/2 clean case images and n/2 augmented, alternating document types."""
    rng = random.Random(seed)
    half = n // 2

    def spread(items: list[dict], k: int) -> list[dict]:
        by_doc: dict[str, list[dict]] = {}
        for it in items:
            by_doc.setdefault(it["doc"], []).append(it)
        for v in by_doc.values():
            rng.shuffle(v)
        docs, out = sorted(by_doc), []
        while len(out) < k and any(by_doc.values()):
            for d in docs:
                if by_doc[d] and len(out) < k:
                    out.append(by_doc[d].pop())
        return out

    clean = [
        {"id": f"{p.parent.name}_{p.stem}", "png": p, "doc": p.stem, "source": "clean"}
        for p in sorted((data / "synthetic/cases").glob("*/*.png"))
    ]
    with (data / "augmented/manifest.csv").open(encoding="utf-8") as f:
        augmented = [
            {
                "id": Path(r["output"]).stem,
                "png": data / "augmented" / r["output"],
                "doc": r["doc_type"],
                "source": r["preset"],
            }
            for r in csv.DictReader(f)
        ]
    return spread(clean, half) + spread(augmented, n - half)


def share(rows: list[dict], kinds: tuple[str, ...], match: str) -> float | None:
    total = sum(r[f"{k}_total"] for r in rows for k in kinds)
    hit = sum(r[f"{k}_{match}"] for r in rows for k in kinds)
    return 100 * hit / total if total else None


def rate(rows: list[dict], kinds: tuple[str, ...], match: str) -> str:
    v = share(rows, kinds, match)
    return "-" if v is None else f"{v:.1f}%"


def mean_conf(rows: list[dict]) -> str:
    vals = [r["conf"] for r in rows if r["conf"] is not None]
    return f"{sum(vals) / len(vals):.1f}" if vals else "-"


def write_report(rows: list[dict], path: Path) -> None:
    lines = [
        "# OCR preview",
        "",
        "Field found rate = share of ground-truth identifiers (khatian_no, dag_no, case_no, "
        "deed_no; Bangla digits) and printed names (owners, sellers, buyers, heirs) that appear "
        f"in the OCR text. Exact = substring; fuzzy = rapidfuzz partial ratio >= {FUZZY_MIN}.",
        "",
        "| image | doc | source | psm | mean conf | ids exact | ids fuzzy "
        "| names exact | names fuzzy |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        conf = "-" if r["conf"] is None else f"{r['conf']:.1f}"
        lines.append(
            f"| {r['id']} | {r['doc']} | {r['source']} | {r['psm']} | {conf} "
            f"| {r['ids_exact']}/{r['ids_total']} | {r['ids_fuzzy']}/{r['ids_total']} "
            f"| {r['names_exact']}/{r['names_total']} | {r['names_fuzzy']}/{r['names_total']} |"
        )
    lines += [
        "",
        "## Averages per psm",
        "",
        "| psm | group | images | mean conf | ids exact | ids fuzzy | names exact "
        "| names fuzzy | all fuzzy |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for psm in PSMS:
        for group, keep in (
            ("clean", lambda r: r["source"] == "clean"),
            ("augmented", lambda r: r["source"] != "clean"),
            ("all", lambda r: True),
        ):
            sel = [r for r in rows if r["psm"] == psm and keep(r)]
            lines.append(
                f"| {psm} | {group} | {len(sel)} | {mean_conf(sel)} "
                f"| {rate(sel, ('ids',), 'exact')} | {rate(sel, ('ids',), 'fuzzy')} "
                f"| {rate(sel, ('names',), 'exact')} | {rate(sel, ('names',), 'fuzzy')} "
                f"| {rate(sel, BOTH, 'fuzzy')} |"
            )
    score = {p: share([r for r in rows if r["psm"] == p], BOTH, "fuzzy") or 0 for p in PSMS}
    best = ", ".join(str(p) for p in PSMS if score[p] == max(score.values()))
    lines += ["", f"Best psm (highest fuzzy found rate, ids + names, all images): **{best}**"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def counts(ids: set[str], names: set[str], text: str) -> dict:
    ids_exact, ids_fuzzy = found(ids, text)
    names_exact, names_fuzzy = found(names, text)
    return {
        "ids_total": len(ids),
        "ids_exact": ids_exact,
        "ids_fuzzy": ids_fuzzy,
        "names_total": len(names),
        "names_exact": names_exact,
        "names_fuzzy": names_fuzzy,
    }


def run_grid(items: list[dict], path: Path) -> None:
    pages = []  # preprocess once per image
    for item in items:
        gt = json.loads(item["png"].with_suffix(".json").read_text(encoding="utf-8"))
        pre = preprocess(item["png"].read_bytes())
        pages.append((item, *expected_values(gt), pre))

    results = []
    for inp, scale, lang, model in itertools.product(
        ("binary", "gray"), (1, 2), ("ben", "ben+eng"), ("apt", "best")
    ):
        os.environ["TESSDATA_PREFIX"] = TESSDATA[model]
        tesseract_version.cache_clear()  # language check must look at the selected folder
        rows, seconds = [], 0.0
        for item, ids, names, pre in pages:
            img = getattr(pre, inp)
            start = time.perf_counter()
            if scale != 1:
                img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            res = ocr(img, lang=lang, psm=3)
            seconds += time.perf_counter() - start
            rows.append({**item, "conf": res.mean_confidence, **counts(ids, names, nfc(res.text))})
        combo = f"{inp} {scale}x {lang} {model}"
        print(f"{combo}: {seconds / len(pages):.1f} s/image")
        results.append((combo, rows, seconds / len(pages)))

    def group(rows, clean):
        return [r for r in rows if (r["source"] == "clean") == clean]

    results.sort(
        key=lambda c: (
            share(group(c[1], False), BOTH, "fuzzy") or 0,
            share(group(c[1], True), BOTH, "fuzzy") or 0,
        ),
        reverse=True,
    )
    lines = [
        "# OCR settings grid (psm 3)",
        "",
        f"{len(pages)} images (same pick as report.md). Fuzzy = rapidfuzz partial ratio "
        f">= {FUZZY_MIN}. Sorted by augmented all fuzzy, then clean all fuzzy. "
        "Seconds per image = upscale + OCR (preprocess excluded).",
        "",
        "| input | scale | lang | model | clean ids | clean names | clean all | clean conf "
        "| aug ids | aug names | aug all | aug conf | s/image |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for combo, rows, sec in results:
        cells = []
        for clean in (True, False):
            g = group(rows, clean)
            cells += [
                rate(g, ("ids",), "fuzzy"),
                rate(g, ("names",), "fuzzy"),
                rate(g, BOTH, "fuzzy"),
                mean_conf(g),
            ]
        lines.append(f"| {' | '.join(combo.split())} | {' | '.join(cells)} | {sec:.1f} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--data-root", type=Path, default=DATA)
    ap.add_argument("--out", type=Path, help="default: <data-root>/preview/ocr")
    ap.add_argument("--grid", action="store_true", help="settings grid -> grid.md")
    args = ap.parse_args()
    args.out = args.out or args.data_root / "preview" / "ocr"

    args.out.mkdir(parents=True, exist_ok=True)
    if args.grid:
        run_grid(pick(args.n, args.seed, args.data_root), args.out / "grid.md")
        print(f"wrote {args.out / 'grid.md'}")
        return
    rows = []
    for item in pick(args.n, args.seed, args.data_root):
        gt = json.loads(item["png"].with_suffix(".json").read_text(encoding="utf-8"))
        ids, names = expected_values(gt)
        binary = preprocess(item["png"].read_bytes()).binary
        for psm in PSMS:
            res = ocr(binary, psm=psm)
            text = nfc(res.text)
            (args.out / f"{item['id']}_psm{psm}.txt").write_text(
                text + "\n", encoding="utf-8", newline="\n"
            )
            row = {**item, "psm": psm, "conf": res.mean_confidence, **counts(ids, names, text)}
            rows.append(row)
            print(f"{item['id']} psm{psm}: conf={row['conf']} ids {row['ids_fuzzy']}/{len(ids)}")
    write_report(rows, args.out / "report.md")
    print(f"wrote {args.out / 'report.md'}")


if __name__ == "__main__":
    main()
