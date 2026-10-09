"""Synthetic sale-deed cases: one khatian + one deed per case, some with one injected mismatch.

Usage (from ml/):
    PYTHONPATH=../backend uv run python -m synth.deed --n 50 --seed 43 --mismatch-rate 0.4 \
        --out ../data/synthetic/cases
"""

import argparse
import csv
import json
import random
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

from app.schemas.extracted import DeedData, KhatianData, Owner

from synth.common import (
    PLACES,
    Renderer,
    acres_text,
    choose_font,
    is_female,
    item_seeds,
    person,
    to_bn,
)
from synth.khatian import SURVEY_LABELS, identifier
from synth.khatian import build as build_khatian

MISMATCH_TYPES = (
    "area_exceeds_share",
    "seller_not_owner",
    "dag_mismatch",
    "khatian_mismatch",
    "mouza_mismatch",
)
MISMATCH_FIELDS = {
    "area_exceeds_share": "transferred_area_shatangsho",
    "seller_not_owner": "sellers[0].name_normalized",
    "dag_mismatch": "schedule_plots[0].dag_no",
    "khatian_mismatch": "schedule_khatians[0].khatian_no",
    "mouza_mismatch": "schedule_location.mouza",
}
DEED_TYPES = {"saf_kabala": "সাফ কবলা দলিল", "heba": "হেবা দলিল", "dan": "দানপত্র দলিল"}
DEED_TYPE_WEIGHTS = [85, 10, 5]
TITLE_SOURCES = ["ওয়ারিশ সূত্রে প্রাপ্ত", "ক্রয় সূত্রে প্রাপ্ত"]
MARKERS = {"father": "পিতা", "husband": "স্বামী"}


@dataclass
class Case:
    id: str
    seed: int
    khatian_font: str
    deed_font: str
    khatian: KhatianData
    khatian_printed: dict
    deed: DeedData
    deed_printed: dict
    benign_name_variation: bool
    mismatches: list[dict] = field(default_factory=list)

    def khatian_json(self) -> str:
        return self.khatian.model_dump_json(indent=2, exclude_none=True) + "\n"

    def deed_json(self) -> str:
        return self.deed.model_dump_json(indent=2, exclude_none=True) + "\n"

    def case_json(self) -> str:
        case = {
            "case_id": self.id,
            "seed": self.seed,
            "seller_name": self.deed.sellers[0].name,
            "benign_name_variation": self.benign_name_variation,
            "mismatches": self.mismatches,
        }
        return json.dumps(case, ensure_ascii=False, indent=2) + "\n"


# --- printing helpers ---


def money_text(taka: int) -> str:
    """6000000 -> "৬০,০০,০০০/- টাকা" (lakh grouping)."""
    s = str(taka)
    head, groups = s[:-3], [s[-3:]]
    while head:
        groups.insert(0, head[-2:])
        head = head[:-2]
    return f"{to_bn(','.join(groups))}/- টাকা"


def shatangsho_text(tt: int) -> str:
    """Ten-thousandths of an acre (multiple of 50) -> "১০" / "৬.৫"."""
    whole, frac = divmod(tt, 100)
    return to_bn(str(whole) if frac == 0 else f"{whole}.{frac:02d}".rstrip("0"))


def date_text(d: date) -> str:
    return to_bn(d.strftime("%d/%m/%Y"))


def toggle_honorific(rng: random.Random, owner: Owner) -> str:
    """Same person, printed with/without an honorific, differently from the khatian."""
    if owner.name != owner.name_normalized:
        return owner.name_normalized
    hon = "মোছাঃ" if is_female(owner.name_normalized) else rng.choice(["মোঃ", "শেখ"])
    return f"{hon} {owner.name_normalized}"


def other_mouza(rng: random.Random, khatian: KhatianData) -> str:
    loc = khatian.location
    district = next(d for d in PLACES["districts"] if d["name"] == loc.district)
    upazila = next(u for u in district["upazilas"] if u["name"] == loc.upazila)
    return rng.choice([m for m in upazila["mouzas"] if m != loc.mouza])


def sale_limit_tt(owner: Owner, plot) -> int:
    """Seller's share of one dag, in ten-thousandths of an acre (rounded down)."""
    return int(owner.share_fraction * plot.area_shatangsho * 100)


# --- the deed ---


def build_deed(
    rng: random.Random, khatian: KhatianData, mismatch: str | None
) -> tuple[DeedData, dict, bool, list[dict]]:
    loc = khatian.location
    options = [(o, p) for o in khatian.owners for p in khatian.plots if sale_limit_tt(o, p) >= 1]
    seller, plot = rng.choice(options)

    # transferred area, in ten-thousandths of an acre (exact Decimal below)
    if mismatch == "area_exceeds_share":  # demo case: share 6, sold 10
        tt = 50 * (int(seller.share_shatangsho * 100 // 50) + rng.randint(1, 8))
        in_acres = False
    else:
        limit = sale_limit_tt(seller, plot)
        in_acres = limit < 50 or rng.random() < 0.5
        tt = rng.randint(1, limit) if in_acres else 50 * rng.randint(1, limit // 50)
    area_shatangsho = Decimal(tt).scaleb(-2)
    if in_acres:
        area_text = f"{acres_text(Decimal(tt).scaleb(-4))} একর"
    else:
        area_text = f"{shatangsho_text(tt)} শতাংশ"

    # seller as printed on the deed
    benign = mismatch is None and rng.random() < 0.3
    if mismatch == "seller_not_owner":
        owner_names = {o.name_normalized for o in khatian.owners}
        name, plain, guardian, marker = person(rng)
        while plain in owner_names:
            name, plain, guardian, marker = person(rng)
    else:
        name = toggle_honorific(rng, seller) if benign else seller.name
        plain, guardian = seller.name_normalized, seller.father_or_husband_name
        marker = seller.relation_marker
    seller_d = {
        "name": name,
        "name_normalized": plain,
        "father_or_husband_name": guardian,
        "relation_marker": marker,
        "address_text": f"সাং- {loc.mouza}, উপজেলা- {loc.upazila}, জেলা- {loc.district}",
    }

    b_name, b_plain, b_guardian, b_marker = person(rng)
    b_district = rng.choice(PLACES["districts"])
    b_upazila = rng.choice(b_district["upazilas"])
    buyer_d = {
        "name": b_name,
        "name_normalized": b_plain,
        "father_or_husband_name": b_guardian,
        "relation_marker": b_marker,
        "address_text": f"সাং- {rng.choice(b_upazila['mouzas'])}, "
        f"উপজেলা- {b_upazila['name']}, জেলা- {b_district['name']}",
    }

    # schedule (তফসিল)
    mouza = other_mouza(rng, khatian) if mismatch == "mouza_mismatch" else loc.mouza
    khatian_no = khatian.khatian_no
    while mismatch == "khatian_mismatch" and khatian_no == khatian.khatian_no:
        khatian_no = identifier(rng, rng.randint(1, 2500))
    refs = [{"survey_type": khatian.survey_type, "khatian_no": khatian_no}]
    if khatian.survey_type in ("RS", "BS") and rng.random() < 0.4:
        refs.append({"survey_type": "SA", "khatian_no": str(rng.randint(1, 2500))})
    dag_no = plot.dag_no
    khatian_dags = {p.dag_no for p in khatian.plots}
    while mismatch == "dag_mismatch" and dag_no in khatian_dags:
        dag_no = identifier(rng, rng.randint(1, 3000))

    # header, price, history
    deed_type = rng.choices(list(DEED_TYPES), weights=DEED_TYPE_WEIGHTS)[0]
    is_draft = rng.random() < 0.3
    year = rng.randint(2005, 2025)
    reg_date = None if is_draft else date(year, rng.randint(1, 12), rng.randint(1, 28))
    deed_no = None if is_draft else str(rng.randint(100, 15000))
    price = None
    if deed_type == "saf_kabala":  # gifts (heba, dan) carry no price
        per_shatangsho = Decimal(rng.randint(50, 800) * 1000)
        price = max(1, int((per_shatangsho * area_shatangsho / 1000).to_integral_value())) * 1000
    prior_deeds = [
        {"deed_no": str(rng.randint(100, 15000)), "deed_year": str(rng.randint(1960, year - 1))}
        for _ in range(rng.randint(1, 2) if rng.random() < 0.4 else 0)
    ]
    title = TITLE_SOURCES[1] if prior_deeds else rng.choice(TITLE_SOURCES)
    witnesses = [person(rng) for _ in range(2)]  # distractor text only, not in ground truth

    deed = DeedData.model_validate(
        {
            "doc_type": "deed",
            "deed_type": deed_type,
            "is_draft": is_draft,
            "deed_no": deed_no,
            "deed_year": None if is_draft else str(year),
            "registration_date": reg_date,
            "registration_date_text": date_text(reg_date) if reg_date else None,
            "sub_registry_office": loc.upazila,
            "book_no": None if is_draft else "1",
            "sellers": [seller_d],
            "buyers": [buyer_d],
            "price_taka": price,
            "price_text": money_text(price) if price else None,
            "schedule_location": {
                "district": loc.district,
                "upazila": loc.upazila,
                "mouza": mouza,
                "jl_no": loc.jl_no,
            },
            "schedule_khatians": refs,
            "schedule_plots": [
                {
                    "dag_no": dag_no,
                    "land_class": plot.land_class,
                    "area_text": area_text,
                    "area_shatangsho": area_shatangsho,
                }
            ],
            "transferred_area_text": area_text,
            "transferred_area_shatangsho": area_shatangsho,
            "prior_deeds": prior_deeds,
            "title_source_text": title,
        }
    )

    def party(p: dict) -> dict:
        return {**p, "marker": MARKERS[p["relation_marker"]]}

    printed = {
        "deed_label": DEED_TYPES[deed_type],
        "is_draft": is_draft,
        "deed_no": to_bn(deed_no) if deed_no else None,
        "deed_year": to_bn(str(year)) if not is_draft else None,
        "registration_date_text": deed.registration_date_text,
        "sub_registry_office": loc.upazila,
        "book_no": to_bn("1") if not is_draft else None,
        "sellers": [party(seller_d)],
        "buyers": [party(buyer_d)],
        "title_source_text": title,
        "prior_deeds": [f"{to_bn(d['deed_no'])}/{to_bn(d['deed_year'])}" for d in prior_deeds],
        "district": loc.district,
        "upazila": loc.upazila,
        "mouza": mouza,
        "jl_no": to_bn(loc.jl_no),
        "khatian_refs": ", ".join(
            f"{SURVEY_LABELS[r['survey_type']]} {to_bn(r['khatian_no'])}" for r in refs
        ),
        "dag_no": to_bn(dag_no),
        "land_class": plot.land_class,
        "area_text": area_text,
        "price_text": deed.price_text,
        "witnesses": [
            {
                "serial": to_bn(str(i)),
                "name": w[0],
                "marker": MARKERS[w[3]],
                "father_or_husband_name": w[2],
            }
            for i, w in enumerate(witnesses, 1)
        ],
    }

    mismatches = []
    if mismatch:
        khatian_value, deed_value = {
            "area_exceeds_share": (seller.share_shatangsho, area_shatangsho),
            "seller_not_owner": (seller.name_normalized, plain),
            "dag_mismatch": (plot.dag_no, dag_no),
            "khatian_mismatch": (khatian.khatian_no, khatian_no),
            "mouza_mismatch": (loc.mouza, mouza),
        }[mismatch]
        mismatches.append(
            {
                "type": mismatch,
                "field": MISMATCH_FIELDS[mismatch],
                "khatian_value": str(khatian_value),
                "deed_value": str(deed_value),
            }
        )
    return deed, printed, benign, mismatches


def generate_cases(n: int, seed: int, mismatch_rate: float = 0.4) -> list[Case]:
    cases = []
    for i, item_seed in enumerate(item_seeds(seed, n), 1):
        rng = random.Random(item_seed)
        khatian_font = choose_font(rng)
        khatian, khatian_printed = build_khatian(rng)
        deed_font = choose_font(rng)
        mismatch = rng.choice(MISMATCH_TYPES) if rng.random() < mismatch_rate else None
        deed, deed_printed, benign, mismatches = build_deed(rng, khatian, mismatch)
        cases.append(
            Case(
                f"case_{i:05d}",
                item_seed,
                khatian_font,
                deed_font,
                khatian,
                khatian_printed,
                deed,
                deed_printed,
                benign,
                mismatches,
            )
        )
    return cases


def generate(n: int, seed: int, mismatch_rate: float, out: Path) -> list[Case]:
    out.mkdir(parents=True, exist_ok=True)
    cases = generate_cases(n, seed, mismatch_rate)
    with Renderer() as renderer:
        for c in cases:
            d = out / c.id
            d.mkdir(exist_ok=True)
            renderer.render("khatian.html", c.khatian_font, c.khatian_printed, d / "khatian.png")
            renderer.render("deed.html", c.deed_font, c.deed_printed, d / "deed.png")
            (d / "khatian.json").write_text(c.khatian_json(), encoding="utf-8")
            (d / "deed.json").write_text(c.deed_json(), encoding="utf-8")
            (d / "case.json").write_text(c.case_json(), encoding="utf-8")

    with (out / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "case_id",
                "seed",
                "khatian_font",
                "deed_font",
                "survey_type",
                "deed_type",
                "is_draft",
                "benign_name_variation",
                "mismatch_type",
            ]
        )
        for c in cases:
            w.writerow(
                [
                    c.id,
                    c.seed,
                    c.khatian_font,
                    c.deed_font,
                    c.khatian.survey_type,
                    c.deed.deed_type,
                    c.deed.is_draft,
                    c.benign_name_variation,
                    c.mismatches[0]["type"] if c.mismatches else "",
                ]
            )
    return cases


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--seed", type=int, default=43)
    ap.add_argument("--mismatch-rate", type=float, default=0.4)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    cases = generate(args.n, args.seed, args.mismatch_rate, args.out)
    print(f"wrote {len(cases)} cases to {args.out}")


if __name__ == "__main__":
    main()
