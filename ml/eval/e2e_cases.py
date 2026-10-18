"""End-to-end evaluation on synthetic cases: images -> classify -> extract -> normalize -> land
case -> rules -> assessment, compared with each case's mismatch labels (case.json).

Usage (Docker/Linux, from ml/, PYTHONPATH=../backend; Tesseract needed for classify):
    python -m eval.e2e_cases --split test --limit 20 --name e2e_v1 [--extractor tesseract_regex]
The extractor defaults to the EXTRACTOR setting (through the LLM cache and budget guard).
Writes <out>/<name>/report.md and cases.csv; stops cleanly on BudgetExceeded.

Expected codes are the case.json mismatch types (same names as findings.md codes). In family
cases, heir_consent_missing next to an expected area_exceeds_share is allowed, not an extra.
For every miss and false alarm the extraction fields that differ from the ground truth are
listed, so we can tell an extraction error from a rule error.
"""

import argparse
import csv
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from app.schemas.land_case import CaseDocumentInput
from app.services.extraction import BudgetExceeded
from app.services.land_case import build_land_case
from app.services.normalize import normalize_document
from app.services.risk import assess
from app.services.rules import Status, run_rules

from eval.compare import MODELS, compare_documents, normalized
from eval.extraction import DATA, ML

LABEL_CODES = {"area_exceeds_share", "seller_not_owner", "dag_mismatch", "khatian_mismatch",
               "mouza_mismatch"}  # fmt: skip
ALLOWED_WITH = {"heir_consent_missing": "area_exceeds_share"}  # family cases
DOC_FILES = ("khatian", "deed", "mutation", "heir_cert")


@dataclass
class CaseResult:
    case_id: str
    family: bool
    expected: set[str]
    found_bad: set[str] = field(default_factory=set)
    found_warn: set[str] = field(default_factory=set)
    risk: str | None = None
    unread: list[str] = field(default_factory=list)  # documents not classified or extracted
    causes: list[str] = field(default_factory=list)  # wrong extraction fields, if relevant
    error: str | None = None

    @property
    def found(self) -> set[str]:
        return self.found_bad | self.found_warn

    def allowed(self) -> set[str]:
        return {c for c, needs in ALLOWED_WITH.items() if self.family and needs in self.expected}

    @property
    def missed(self) -> set[str]:
        return self.expected - self.found

    @property
    def extra_bad(self) -> set[str]:
        return self.found_bad - self.expected - self.allowed()

    @property
    def extra_warn(self) -> set[str]:
        return self.found_warn - self.expected - self.allowed()


def wrong_fields(gt, pred) -> list[str]:
    """Critical extraction fields where the prediction differs from the ground truth."""
    if pred is None:
        return ["(nothing extracted)"]
    c = compare_documents(normalized(gt), normalized(pred))
    return [
        f"{f.path}: {f.expected!r} -> {f.predicted!r}"
        for f in c.fields
        if f.critical and f.correct is False and f.gt_present
    ]


def run_case(
    case_id: str,
    family: bool,
    expected: set[str],
    documents: list[tuple[str, bytes, object]],  # (file name, image bytes, ground-truth model)
    extractor,
    classify: Callable[[bytes], str],
) -> CaseResult:
    """One case through the pipeline steps. Raises BudgetExceeded (caller stops)."""
    result = CaseResult(case_id, family, expected)
    inputs, predicted = [], {}
    for name, image, _ in documents:
        doc_type = classify(image)
        if doc_type not in MODELS:
            result.unread.append(f"{name}: classified as {doc_type}")
            continue
        ex = extractor.extract(image, doc_type)
        if ex.document is None:
            result.unread.append(f"{name}: {ex.error}")
            continue
        norm = normalize_document(ex.document)
        predicted[name] = ex.document
        flags: dict[str, list[str]] = {}
        for w in norm.warnings:
            flags.setdefault(w.field_path, []).append(w.code)
        status = "needs_review" if flags else "ok"
        inputs.append(
            CaseDocumentInput(
                source_id=name, data=norm.doc, field_flags=flags, extraction_status=status
            )
        )
    case = build_land_case(inputs)
    run = run_rules(case)
    result.found_bad = {f.code for f in run.findings if f.status == Status.bad}
    result.found_warn = {f.code for f in run.findings if f.status == Status.warn}
    result.risk = assess(case, run).risk_level
    if result.missed or result.extra_bad or result.extra_warn:
        for name, _, gt in documents:
            for wrong in wrong_fields(gt, predicted.get(name)):
                result.causes.append(f"{name}: {wrong}")
    return result


def metrics(results: list[CaseResult]) -> dict:
    per_type = {}
    for code in sorted(LABEL_CODES):
        with_it = [r for r in results if code in r.expected]
        found = [r for r in with_it if code in r.found]
        per_type[code] = (len(found), len(with_it))
    clean = [r for r in results if not r.expected]
    return {
        "cases": len(results),
        "detection": per_type,
        "detected": sum(f for f, _ in per_type.values()),
        "expected": sum(n for _, n in per_type.values()),
        "clean_cases": len(clean),
        "false_alarms": sum(bool(r.extra_bad) for r in clean),
        "extra_warn_clean": sum(bool(r.extra_warn) for r in clean),
        "unread_documents": sum(len(r.unread) for r in results),
    }


def pct(n: int, d: int) -> str:
    return f"{100 * n / d:.0f}% ({n}/{d})" if d else "-"


def report_md(name: str, results: list[CaseResult], m: dict, args: dict, stopped: str | None):
    lines = [
        f"# End-to-end eval: {name}",
        "",
        f"Split `{args['split']}`, extractor `{args['extractor']}`, images `{args['images']}`, "
        f"{m['cases']} cases ({m['clean_cases']} clean). Unread documents: "
        f"{m['unread_documents']}." + (f" **Stopped early:** {stopped}" if stopped else ""),
        "",
        "| measure | value |",
        "|---|---|",
        f"| detection (all labelled mismatches) | {pct(m['detected'], m['expected'])} |",
        f"| false alarm rate (clean cases with an extra bad finding) | "
        f"{pct(m['false_alarms'], m['clean_cases'])} |",
        f"| extra-warn rate on clean cases | {pct(m['extra_warn_clean'], m['clean_cases'])} |",
        "",
        "| mismatch type | detected |",
        "|---|---|",
        *(f"| {c} | {pct(f, n)} |" for c, (f, n) in m["detection"].items()),
        "",
        "## Cases",
        "",
        "| case | expected | found bad | found warn | missed | extra | risk | unread |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        extra = sorted(r.extra_bad | r.extra_warn)
        lines.append(
            f"| {r.case_id} | {', '.join(sorted(r.expected)) or '-'} | "
            f"{', '.join(sorted(r.found_bad)) or '-'} | {', '.join(sorted(r.found_warn)) or '-'} | "
            f"{', '.join(sorted(r.missed)) or '-'} | {', '.join(extra) or '-'} | {r.risk} | "
            f"{len(r.unread)} |"
        )
    lines += ["", "## Causes (misses and false alarms)", ""]
    for r in results:
        if r.missed or r.extra_bad or r.extra_warn:
            what = [f"missed {', '.join(sorted(r.missed))}"] if r.missed else []
            what += [f"extra {', '.join(sorted(r.extra_bad | r.extra_warn))}"] if (
                r.extra_bad or r.extra_warn) else []  # fmt: skip
            kind = "extraction" if r.causes or r.unread else "rule (extraction matched)"
            lines.append(f"- **{r.case_id}** ({'; '.join(what)}): cause = {kind}")
            lines += [f"  - unread: {u}" for u in r.unread]
            lines += [f"  - {c}" for c in r.causes[:12]]
            if len(r.causes) > 12:
                lines.append(f"  - … and {len(r.causes) - 12} more wrong fields")
    return "\n".join(lines) + "\n"


def load_cases(split: str, data_root: Path, dataset: str) -> list[str]:
    manifest = json.loads((ML / "datasets" / f"{dataset}.json").read_text(encoding="utf-8"))
    return sorted({
        f["source_id"] for f in manifest["files"]
        if f["path"].startswith("synthetic/cases/") and f["path"].endswith("/case.json")
        and (split == "all" or f.get("split") == split)
    })  # fmt: skip


def case_documents(case_dir: Path, data_root: Path, images: str):
    """(file name, image bytes, ground truth) for each document of the case."""
    out = []
    for doc in DOC_FILES:
        gt_path = case_dir / f"{doc}.json"
        if not gt_path.exists():
            continue
        raw = json.loads(gt_path.read_text(encoding="utf-8"))
        gt = MODELS[raw["doc_type"]].model_validate(raw)
        if images == "clean":
            png = case_dir / f"{doc}.png"
        else:  # augmented copy k: augmented/<case>_<doc>_<k>.png
            png = data_root / "augmented" / f"{case_dir.name}_{doc}_{images[-1]}.png"
        out.append((f"{doc}.json", png.read_bytes(), gt))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--split", choices=["test", "train", "all"], default="test")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--sample", type=Path, help="only cases listed in a sample JSON file")
    ap.add_argument("--name", default="e2e_v1")
    ap.add_argument("--extractor", help="default: the EXTRACTOR setting")
    ap.add_argument("--images", choices=["clean", "aug0", "aug1"], default="clean")
    ap.add_argument("--dataset", default="v2")
    ap.add_argument("--data-root", type=Path, default=DATA)
    ap.add_argument("--out", type=Path, default=DATA / "eval")
    a = ap.parse_args()

    from app.core.config import settings
    from app.services.classify import classify_image
    from app.services.pipeline import make_extractor

    name = a.extractor or settings.extractor
    extractor = make_extractor(name)
    case_ids = load_cases(a.split, a.data_root, a.dataset)[: a.limit]
    if a.sample:
        wanted = set(json.loads(a.sample.read_text(encoding="utf-8"))["cases"])
        case_ids = [
            case_id for case_id in load_cases(a.split, a.data_root, a.dataset) if case_id in wanted
        ]
    results, stopped = [], None
    for case_id in case_ids:
        case_dir = a.data_root / "synthetic/cases" / case_id
        label = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
        expected = {m["type"] for m in label["mismatches"]} & LABEL_CODES
        try:
            r = run_case(case_id, label["family"], expected,
                         case_documents(case_dir, a.data_root, a.images), extractor,
                         lambda b: classify_image(b).doc_type)  # fmt: skip
        except BudgetExceeded as e:
            stopped = str(e)
            print(f"stopped: {e}")
            break
        results.append(r)
        print(f"{case_id}: expected {sorted(r.expected)} found {sorted(r.found)} risk {r.risk}")

    m = metrics(results)
    run_dir = a.out / a.name
    run_dir.mkdir(parents=True, exist_ok=True)
    args = {"split": a.split, "extractor": name, "images": a.images}
    (run_dir / "report.md").write_text(report_md(a.name, results, m, args, stopped),
                                       encoding="utf-8", newline="\n")  # fmt: skip
    with (run_dir / "cases.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["case", "family", "expected", "found_bad", "found_warn", "missed",
                    "extra_bad", "extra_warn", "risk", "unread", "causes"])  # fmt: skip
        for r in results:
            w.writerow([r.case_id, r.family, ";".join(sorted(r.expected)),
                        ";".join(sorted(r.found_bad)), ";".join(sorted(r.found_warn)),
                        ";".join(sorted(r.missed)), ";".join(sorted(r.extra_bad)),
                        ";".join(sorted(r.extra_warn)), r.risk, len(r.unread),
                        " | ".join(r.causes)])  # fmt: skip
    print(f"detection {pct(m['detected'], m['expected'])}, false alarms "
          f"{pct(m['false_alarms'], m['clean_cases'])}, extra warn "
          f"{pct(m['extra_warn_clean'], m['clean_cases'])}")  # fmt: skip
    print(f"wrote {run_dir}")


if __name__ == "__main__":
    main()
