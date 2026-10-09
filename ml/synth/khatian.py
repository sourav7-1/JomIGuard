"""Synthetic khatian generator: HTML template -> PNG (Playwright) + ground-truth JSON.

Usage (from ml/):
    PYTHONPATH=../backend uv run python -m synth.khatian --n 50 --seed 42 \
        --out ../data/synthetic/khatian
"""

import argparse
import csv
import random
from dataclasses import dataclass
from decimal import Decimal
from itertools import pairwise
from pathlib import Path

from app.schemas.extracted import KhatianData

from synth.common import (
    NAMES,
    PLACES,
    Renderer,
    acres_text,
    choose_font,
    item_seeds,
    person,
    to_bn,
)
from synth.common import to_ascii as to_ascii  # re-export (tests import it from here)

SURVEY_LABELS = {"CS": "সি.এস.", "SA": "এস.এ.", "RS": "আর.এস.", "BS": "বি.এস."}
MARKERS = {"father": "পিং", "husband": "জং"}
AREA_UNIT = "একর"  # printed only in the area column headers of templates/khatian.html


@dataclass
class Record:
    id: str
    seed: int
    font: str
    khatian: KhatianData
    printed: dict  # template context: exactly what appears on the image

    def ground_truth_json(self) -> str:
        return self.khatian.model_dump_json(indent=2, exclude_none=True) + "\n"


def share_text(thousandths: int) -> str:
    return to_bn("1.000" if thousandths == 1000 else f".{thousandths:03d}")


def identifier(rng: random.Random, base: int) -> str:
    return f"{base}/{rng.randint(1, 3)}" if rng.random() < 0.2 else str(base)


def split_thousandths(rng: random.Random, n: int) -> list[int]:
    """n positive integers summing to exactly 1000."""
    if rng.random() < 0.5:  # equal split, remainder to the first owner (".৩৩৪")
        each = 1000 // n
        return [1000 - each * (n - 1)] + [each] * (n - 1)
    cuts = sorted(rng.sample(range(1, 1000), n - 1))
    return [b - a for a, b in pairwise([0, *cuts, 1000])]


def build(rng: random.Random) -> tuple[KhatianData, dict]:
    survey = rng.choice(list(SURVEY_LABELS))
    district = rng.choice(PLACES["districts"])
    upazila = rng.choice(district["upazilas"])
    mouza = rng.choice(upazila["mouzas"])
    jl_no = str(rng.randint(1, 250))
    khatian_no = identifier(rng, rng.randint(1, 2500))

    plots, printed_plots = [], []
    for base in rng.sample(range(1, 3000), rng.randint(1, 4)):
        total_tt = rng.randint(13, 1250) * 4  # ten-thousandths of an acre; /4 keeps shares exact
        share_k = rng.choices([1000, 500, 250], weights=[7, 2, 1])[0]
        total = Decimal(total_tt).scaleb(-4)
        area = Decimal(total_tt * share_k // 1000).scaleb(-4)
        dag_no = identifier(rng, base)
        p = {
            "dag_no": dag_no,
            "land_class": rng.choice(PLACES["land_classes"]),
            "plot_total_area_text": acres_text(total),
            "plot_total_area_shatangsho": total * 100,
            "khatian_share_text": share_text(share_k),
            "khatian_share_fraction": Decimal(share_k).scaleb(-3),
            "area_text": acres_text(area),
            "area_shatangsho": area * 100,
        }
        plots.append(p)
        printed_plots.append({**p, "dag_no": to_bn(dag_no)})

    total_shatangsho = sum(p["area_shatangsho"] for p in plots)
    total_text = acres_text(total_shatangsho / 100)

    owners, printed_owners = [], []
    shares = split_thousandths(rng, rng.randint(1, 5))
    for i, k in enumerate(shares, 1):
        name, plain, guardian, marker = person(rng)
        fraction = Decimal(k).scaleb(-3)
        o = {
            "name": name,
            "name_normalized": plain,
            "father_or_husband_name": guardian,
            "relation_marker": marker,
            "address_text": f"সাং- {mouza}",
            "share_text": share_text(k),
            "share_fraction": fraction,
            "share_shatangsho": fraction * total_shatangsho,
        }
        owners.append(o)
        printed_owners.append({**o, "serial": to_bn(str(i)), "marker": MARKERS[marker]})

    touzi_no = str(rng.randint(100, 9999)) if survey in ("CS", "SA") else None
    landlord = f"{rng.choice(NAMES['male_first'])} {rng.choice(NAMES['male_last'])}"
    landlord_name = landlord if survey == "CS" else None
    revenue = f"{to_bn(str(rng.randint(1, 40)))} টাকা" if rng.random() < 0.5 else None

    khatian = KhatianData.model_validate(
        {
            "doc_type": "khatian",
            "survey_type": survey,
            "location": {
                "district": district["name"],
                "upazila": upazila["name"],
                "mouza": mouza,
                "jl_no": jl_no,
            },
            "khatian_no": khatian_no,
            "touzi_no": touzi_no,
            "owners": owners,
            "plots": plots,
            "area_unit_text": AREA_UNIT,
            "total_area_text": total_text,
            "total_area_shatangsho": total_shatangsho,
            "annual_revenue_text": revenue,
            "landlord_name": landlord_name,
        }
    )
    printed = {
        "survey_label": SURVEY_LABELS[survey],
        "district": district["name"],
        "upazila": upazila["name"],
        "mouza": mouza,
        "jl_no": to_bn(jl_no),
        "khatian_no": to_bn(khatian_no),
        "touzi_no": to_bn(touzi_no) if touzi_no else None,
        "landlord_name": landlord_name,
        "owners": printed_owners,
        "plots": printed_plots,
        "total_area_text": total_text,
        "annual_revenue_text": revenue,
    }
    return khatian, printed


def generate_records(n: int, seed: int) -> list[Record]:
    records = []
    for i, item_seed in enumerate(item_seeds(seed, n), 1):
        rng = random.Random(item_seed)
        font = choose_font(rng)
        khatian, printed = build(rng)
        records.append(Record(f"khatian_{i:05d}", item_seed, font, khatian, printed))
    return records


def generate(n: int, seed: int, out: Path) -> list[Record]:
    out.mkdir(parents=True, exist_ok=True)
    records = generate_records(n, seed)
    with Renderer() as renderer:
        for r in records:
            renderer.render("khatian.html", r.font, r.printed, out / f"{r.id}.png")
            (out / f"{r.id}.json").write_text(r.ground_truth_json(), encoding="utf-8")

    with (out / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "seed", "font", "survey_type", "owner_count", "plot_count"])
        for r in records:
            k = r.khatian
            w.writerow([r.id, r.seed, r.font, k.survey_type, len(k.owners), len(k.plots)])
    return records


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    generate(args.n, args.seed, args.out)
    print(f"wrote {args.n} khatians to {args.out}")


if __name__ == "__main__":
    main()
