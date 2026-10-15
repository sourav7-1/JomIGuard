"""OCR preview: how many ground-truth values appear in Tesseract's text.

Usage (from ml/):
    PYTHONPATH=../backend uv run python -m eval.ocr_preview --n 20 --seed 1
Picks n/2 clean case images and n/2 augmented images, runs preprocess -> OCR (psm 3, 4, 6),
and writes data/preview/ocr/{image}_psm{psm}.txt plus report.md.
"""

import argparse
import csv
import json
import random
import shutil
import unicodedata
from pathlib import Path

import pytesseract
from app.services.ocr import ocr
from app.services.preprocess import preprocess
from rapidfuzz import fuzz

DATA = Path(__file__).resolve().parents[2] / "data"
PSMS = (3, 4, 6)
ID_KEYS = {"khatian_no", "dag_no", "case_no", "deed_no"}
NAME_LISTS = {"owners", "sellers", "buyers", "heirs"}
FUZZY_MIN = 90
WINDOWS_TESSERACT = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
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


def pick(n: int, seed: int) -> list[dict]:
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
        for p in sorted((DATA / "synthetic/cases").glob("*/*.png"))
    ]
    with (DATA / "augmented/manifest.csv").open(encoding="utf-8") as f:
        augmented = [
            {
                "id": Path(r["output"]).stem,
                "png": DATA / "augmented" / r["output"],
                "doc": r["doc_type"],
                "source": r["preset"],
            }
            for r in csv.DictReader(f)
        ]
    return spread(clean, half) + spread(augmented, n - half)


def rate(rows: list[dict], kind: str) -> str:
    total = sum(r["ids_total"] + r["names_total"] for r in rows)
    hit = sum(r[f"ids_{kind}"] + r[f"names_{kind}"] for r in rows)
    return f"{100 * hit / total:.1f}%" if total else "-"


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
        "## Averages (field found rate, ids + names pooled)",
        "",
        "| psm | group | images | mean conf | exact | fuzzy |",
        "|---|---|---|---|---|---|",
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
                f"| {rate(sel, 'exact')} | {rate(sel, 'fuzzy')} |"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", type=Path, default=DATA / "preview" / "ocr")
    ap.add_argument("--tesseract-cmd", help="path to tesseract if it is not on PATH")
    args = ap.parse_args()

    cmd = args.tesseract_cmd or (
        None if shutil.which("tesseract") or not WINDOWS_TESSERACT.exists() else WINDOWS_TESSERACT
    )
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = str(cmd)

    args.out.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in pick(args.n, args.seed):
        gt = json.loads(item["png"].with_suffix(".json").read_text(encoding="utf-8"))
        ids, names = expected_values(gt)
        binary = preprocess(item["png"].read_bytes()).binary
        for psm in PSMS:
            res = ocr(binary, psm=psm)
            text = nfc(res.text)
            (args.out / f"{item['id']}_psm{psm}.txt").write_text(
                text + "\n", encoding="utf-8", newline="\n"
            )
            ids_exact, ids_fuzzy = found(ids, text)
            names_exact, names_fuzzy = found(names, text)
            rows.append(
                {
                    **item,
                    "psm": psm,
                    "conf": res.mean_confidence,
                    "ids_total": len(ids),
                    "ids_exact": ids_exact,
                    "ids_fuzzy": ids_fuzzy,
                    "names_total": len(names),
                    "names_exact": names_exact,
                    "names_fuzzy": names_fuzzy,
                }
            )
            print(f"{item['id']} psm{psm}: conf={res.mean_confidence} ids {ids_fuzzy}/{len(ids)}")
    write_report(rows, args.out / "report.md")
    print(f"wrote {args.out / 'report.md'}")


if __name__ == "__main__":
    main()
