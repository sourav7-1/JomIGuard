"""Synthetic mutation khatian + DCR receipt (নামজারি খতিয়ান ও ডি.সি.আর.).

Consistent with the case khatian. Used by synth.deed (case assembly).
"""

import random
from datetime import date, timedelta

from app.schemas.extracted import KhatianData, MutationData

from synth.common import to_bn

BASIS = {"inheritance": "ওয়ারিশ সূত্রে", "purchase": "ক্রয় সূত্রে"}


def date_text(d: date) -> str:
    return to_bn(d.strftime("%d/%m/%Y"))


def build_mutation(
    rng: random.Random,
    khatian: KhatianData,
    khatian_printed: dict,
    basis: str,
    after: date | None = None,
) -> tuple[MutationData, dict]:
    """Owners, shares, plots and location are copied from the khatian the mutation created."""
    loc = khatian.location
    if after:  # e.g. the heir certificate's issue date
        order = after + timedelta(days=rng.randint(30, 700))
    else:
        order = date(rng.randint(1990, 2003), rng.randint(1, 12), rng.randint(1, 28))
    case_no = f"{rng.randint(100, 2999)}/{order.year % 100:02d}"
    old_khatian_no = str(rng.randint(1, 2500))  # SA khatian before the mutation
    holding_no = str(rng.randint(1, 999))
    dcr_no = str(rng.randint(100000, 999999))
    dcr_date = order + timedelta(days=rng.randint(1, 30))
    fee = rng.randint(50, 200) * 10  # synthetic amount, not a real fee schedule
    office = f"সহকারী কমিশনার (ভূমি) এর কার্যালয়, {loc.upazila}, {loc.district}"

    mutation = MutationData.model_validate(
        {
            "doc_type": "dcr",
            "case_no": case_no,
            "office": office,
            "location": loc.model_dump(),
            "order_date": order,
            "order_date_text": date_text(order),
            "dcr_no": dcr_no,
            "dcr_date": dcr_date,
            "fee_taka": fee,
            "old_khatian_no": old_khatian_no,
            "new_khatian_no": khatian.khatian_no,
            "holding_no": holding_no,
            "owners": [o.model_dump() for o in khatian.owners],
            "plots": [p.model_dump() for p in khatian.plots],
            "area_unit_text": "একর",  # printed only in the column headers
            "total_area_text": khatian.total_area_text,
            "total_area_shatangsho": khatian.total_area_shatangsho,
            "basis_text": BASIS[basis],
        }
    )
    printed = {
        "case_no": to_bn(case_no),
        "office": office,
        "order_date_text": mutation.order_date_text,
        "district": loc.district,
        "upazila": loc.upazila,
        "mouza": loc.mouza,
        "jl_no": to_bn(loc.jl_no),
        "khatian_no": to_bn(khatian.khatian_no),
        "old_khatian_no": to_bn(old_khatian_no),
        "holding_no": to_bn(holding_no),
        "owners": khatian_printed["owners"],
        "plots": khatian_printed["plots"],
        "total_area_text": khatian_printed["total_area_text"],
        "basis_text": BASIS[basis],
        "dcr_no": to_bn(dcr_no),
        "dcr_date_text": date_text(dcr_date),
        "fee_text": f"{to_bn(f'{fee:,}')}/- টাকা",  # fee < 1 lakh: same grouping as lakh style
    }
    return mutation, printed
