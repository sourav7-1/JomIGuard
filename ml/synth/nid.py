"""Synthetic NID-style cards for the NID name-reading tests: PNG + ground truth (names only).

Every card is fake and watermarked "নমুনা / SAMPLE". The ID number and date of birth are
obvious placeholders (all zeros, year 1900) printed only so tests can prove they are never
read or stored. Never use a real NID for tests.

Usage (from ml/):
    PYTHONPATH=../backend uv run python -m synth.nid --n 10 --seed 45 --out ../data/synthetic/nid
"""

import argparse
import json
import random
from pathlib import Path

from synth.common import NAMES, Renderer, choose_font, item_seeds, person

ID_NO = "০০০০ ০০০ ০০০০"  # placeholder, never a real number
DOB = "01 Jan 1900"


def card(rng: random.Random, i: int) -> dict:
    name, _plain, guardian, marker = person(rng)
    mother = f"{rng.choice(NAMES['female_first'])} {rng.choice(NAMES['female_last'])}"
    return {
        "name_bn": name,
        "name_en": f"SAMPLE PERSON {i:03d}",
        "guardian_label": "স্বামী" if marker == "husband" else "পিতা",
        "guardian": guardian,
        "mother": mother,
        "dob": DOB,
        "id_no": ID_NO,
    }


def truth(c: dict) -> dict:
    """What the reader may return: the three name fields, nothing else."""
    return {"name_bn": c["name_bn"], "name_en": c["name_en"],
            "father_or_husband_name": c["guardian"]}  # fmt: skip


def generate(n: int, seed: int, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    with Renderer() as renderer:
        for i, item_seed in enumerate(item_seeds(seed, n), start=1):
            rng = random.Random(item_seed)
            c = card(rng, i)
            stem = f"nid_{i:03d}"
            renderer.render("nid.html", choose_font(rng), c, out / f"{stem}.png")
            (out / f"{stem}.json").write_text(
                json.dumps(truth(c), ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
            )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--seed", type=int, default=45)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    generate(args.n, args.seed, args.out)
    print(f"wrote {args.n} sample NID cards to {args.out}")


if __name__ == "__main__":
    main()
