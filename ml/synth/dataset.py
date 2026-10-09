"""Freeze the synthetic data as a dataset version, and verify it can be regenerated.

Usage (from ml/):
    uv run python -m synth.dataset build --version v1
    uv run python -m synth.dataset verify --version v1
"""

import argparse
import csv
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from importlib.metadata import version as pkg_version
from pathlib import Path, PurePosixPath

from synth.augment import split_for

ML = Path(__file__).resolve().parents[1]
REPO = ML.parent
BACKEND = REPO / "backend"
DATA = REPO / "data"  # gitignored
DATASETS = ML / "datasets"

# The recipe for v1: run in this order; paths are relative to the data root.
COMMANDS = [
    {"module": "synth.khatian", "args": ["--n", "50", "--seed", "42"], "out": "synthetic/khatian"},
    {
        "module": "synth.deed",
        "args": ["--n", "50", "--seed", "43", "--mismatch-rate", "0.4"],
        "out": "synthetic/cases",
    },
    {
        "module": "synth.augment",
        "args": ["--per-source", "2", "--seed", "44"],
        "src": "synthetic",
        "out": "augmented",
    },
]
LIBRARIES = [
    "playwright",
    "albumentations",
    "opencv-python-headless",
    "numpy",
    "jinja2",
    "pydantic",
]
WARN_ONLY_SUFFIX = ".png"  # rendering can differ by machine; everything else must match exactly


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def arg(command: dict, name: str) -> str | None:
    args = command["args"]
    return args[args.index(name) + 1] if name in args else None


def display(command: dict) -> str:
    parts = ["uv run python -m", command["module"], *command["args"]]
    if "src" in command:
        parts += ["--src", f"../data/{command['src']}"]
    parts += ["--out", f"../data/{command['out']}"]
    prefix = "" if command["module"] == "synth.augment" else "PYTHONPATH=../backend "
    return prefix + " ".join(parts)


def run_commands(commands: list[dict], root: Path) -> None:
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(BACKEND), str(ML)])}
    for c in commands:
        argv = [sys.executable, "-m", c["module"], *c["args"], "--out", str(root / c["out"])]
        if "src" in c:
            argv += ["--src", str(root / c["src"])]
        subprocess.run(argv, cwd=ML, env=env, check=True, stdout=subprocess.DEVNULL)


def data_files(commands: list[dict], root: Path) -> dict[str, Path]:
    """Every file the commands produce, keyed by POSIX path relative to the data root."""
    files = {}
    for c in commands:
        for p in sorted((root / c["out"]).rglob("*")):
            if p.is_file():
                files[p.relative_to(root).as_posix()] = p
    return files


# --- build ---


def describe(rel: str, augmented: dict[str, dict], aug_seed: int | None) -> dict:
    parts = PurePosixPath(rel).parts
    name, stem = parts[-1], PurePosixPath(rel).stem
    if name in ("manifest.csv", "contact_sheet.png"):
        return {"doc_type": stem, "source_id": None, "split": None}
    if parts[0] == "augmented":
        row = augmented[stem]
        return {"doc_type": row["doc_type"], "source_id": row["source_id"], "split": row["split"]}
    if parts[:2] == ("synthetic", "khatian"):
        source_id, doc = stem, "khatian"
    else:  # synthetic/cases/<case_id>/<doc>.<ext>
        source_id, doc = parts[2], stem
    split = split_for(aug_seed, source_id) if aug_seed is not None else None
    return {"doc_type": doc, "source_id": source_id, "split": split}


def counts(root: Path) -> dict:
    cases = read_csv(root / "synthetic/cases/manifest.csv")
    augmented = read_csv(root / "augmented/manifest.csv")

    def tally(rows, key):
        return dict(sorted(Counter(key(r) for r in rows).items()))

    sources = {r["source_id"]: r["split"] for r in augmented}
    return {
        "clean_khatians": len(list((root / "synthetic/khatian").glob("*.json"))),
        "cases": len(cases),
        "case_khatians": len(list((root / "synthetic/cases").glob("*/khatian.json"))),
        "deeds": len(list((root / "synthetic/cases").glob("*/deed.json"))),
        "mismatch_types": tally(cases, lambda r: r["mismatch_type"] or "clean"),
        "augmented": len(augmented),
        "augmented_by_preset": tally(augmented, lambda r: r["preset"]),
        "augmented_by_split": tally(augmented, lambda r: r["split"]),
        "augmented_by_doc_type": tally(augmented, lambda r: r["doc_type"]),
        "sources_by_split": dict(sorted(Counter(sources.values()).items())),
    }


def chromium_version() -> str | None:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            v = browser.version
            browser.close()
            return v
    except Exception:  # noqa: BLE001  informational only
        return None


def git_state() -> dict:
    def git(*args):
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True).stdout

    return {"commit": git("rev-parse", "HEAD").strip(), "dirty": bool(git("status", "--porcelain"))}


def build(version: str, root: Path = DATA, commands=COMMANDS, out: Path | None = None) -> dict:
    augment = next((c for c in commands if c["module"] == "synth.augment"), None)
    aug_seed = int(arg(augment, "--seed")) if augment else None
    augmented = {
        PurePosixPath(r["output"]).stem: r for r in read_csv(root / "augmented/manifest.csv")
    }
    manifest = {
        "version": version,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "code": git_state(),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "chromium": chromium_version(),
            "libraries": {lib: pkg_version(lib) for lib in LIBRARIES},
        },
        "commands": [{**c, "command": display(c)} for c in commands],
        "counts": counts(root),
        "files": [
            {"path": rel, "sha256": sha256(p), **describe(rel, augmented, aug_seed)}
            for rel, p in data_files(commands, root).items()
        ],
    }
    out = out or DATASETS / f"{version}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


# --- verify ---


@dataclass
class Report:
    checked: int = 0
    errors: list[str] = field(default_factory=list)  # non-PNG content mismatches
    png_mismatches: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    extra: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not (self.errors or self.missing or self.extra)


def verify(manifest_path: Path) -> Report:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    commands = [{k: v for k, v in c.items() if k != "command"} for c in manifest["commands"]]
    recorded = {f["path"]: f["sha256"] for f in manifest["files"]}
    report = Report()

    for lib, v in manifest["environment"]["libraries"].items():
        if pkg_version(lib) != v:
            report.warnings.append(f"{lib} {pkg_version(lib)} != recorded {v}")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        run_commands(commands, root)
        regenerated = {rel: sha256(p) for rel, p in data_files(commands, root).items()}

    report.missing = sorted(set(recorded) - set(regenerated))
    report.extra = sorted(set(regenerated) - set(recorded))
    for rel in sorted(set(recorded) & set(regenerated)):
        report.checked += 1
        if recorded[rel] != regenerated[rel]:
            target = report.png_mismatches if rel.endswith(WARN_ONLY_SUFFIX) else report.errors
            target.append(rel)
    return report


def print_report(report: Report) -> None:
    print(f"checked {report.checked} files")
    for w in report.warnings:
        print(f"WARNING: {w}")
    if report.png_mismatches:
        n = len(report.png_mismatches)
        print(f"WARNING: {n} PNG files differ (rendering can vary by machine)")
    for label, items in (
        ("MISMATCH", report.errors),
        ("MISSING", report.missing),
        ("EXTRA", report.extra),
    ):
        for rel in items[:20]:
            print(f"{label}: {rel}")
        if len(items) > 20:
            print(f"{label}: ... and {len(items) - 20} more")
    print("OK" if report.ok else "FAILED")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=["build", "verify"])
    ap.add_argument("--version", required=True)
    ap.add_argument("--data", type=Path, default=DATA, help="data root (build only)")
    args = ap.parse_args()
    path = DATASETS / f"{args.version}.json"
    if args.command == "build":
        m = build(args.version, args.data, out=path)
        print(f"wrote {path} ({len(m['files'])} files)")
    else:
        report = verify(path)
        print_report(report)
        sys.exit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
