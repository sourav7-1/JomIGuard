"""Family cases and synthetic heir certificates (ওয়ারিশ সনদপত্র).

make_family() turns a case khatian's owners into the heirs of one deceased father;
build_heir_cert() writes the certificate for that family. Used by synth.deed (case assembly).
"""

import random
from datetime import date, timedelta
from decimal import Decimal

from app.schemas.extracted import HeirCertData, KhatianData

from synth.common import NAMES, is_female, to_bn
from synth.khatian import MARKERS, share_text, split_thousandths

RELATION_TEXT = {"son": "পুত্র", "daughter": "কন্যা", "wife": "স্ত্রী"}


def date_text(d: date) -> str:
    return to_bn(d.strftime("%d/%m/%Y"))


def new_name(rng: random.Random, sex: str, taken: set[str]) -> str:
    while True:
        plain = f"{rng.choice(NAMES[f'{sex}_first'])} {rng.choice(NAMES[f'{sex}_last'])}"
        if plain not in taken:
            taken.add(plain)
            return plain


def make_family(
    rng: random.Random, khatian: KhatianData, printed: dict
) -> tuple[KhatianData, dict, dict]:
    """Owners become children of one deceased father; sometimes his widow is an owner too.

    The widow is added as a khatian owner (shares re-split) rather than only on the heir
    certificate, so the case carries no unlabeled heir_missing_from_mutation finding.
    """
    taken = {o.name_normalized for o in khatian.owners}
    father = new_name(rng, "male", taken)
    members = [(o.name, o.name_normalized, "father") for o in khatian.owners]
    shares = [int(o.share_fraction * 1000) for o in khatian.owners]
    if len(members) < 5 and rng.random() < 0.3:
        plain = new_name(rng, "female", taken)
        name = f"মোছাঃ {plain}" if rng.random() < 0.6 else plain
        members.append((name, plain, "husband"))
        shares = split_thousandths(rng, len(members))

    total = khatian.total_area_shatangsho
    mouza = khatian.location.mouza
    owners, printed_owners = [], []
    for i, ((name, plain, marker), k) in enumerate(zip(members, shares, strict=True), 1):
        fraction = Decimal(k).scaleb(-3)
        o = {
            "name": name,
            "name_normalized": plain,
            "father_or_husband_name": father,
            "relation_marker": marker,
            "address_text": f"সাং- {mouza}",
            "share_text": share_text(k),
            "share_fraction": fraction,
            "share_shatangsho": fraction * total,
        }
        owners.append(o)
        printed_owners.append({**o, "serial": to_bn(str(i)), "marker": MARKERS[marker]})

    khatian = KhatianData.model_validate({**khatian.model_dump(), "owners": owners})
    deceased = {
        "name": father,
        "father": new_name(rng, "male", taken),
        # family timeline ends before 2005, the earliest deed year in synth.deed
        "date_of_death": date(rng.randint(1985, 1996), rng.randint(1, 12), rng.randint(1, 28)),
    }
    return khatian, {**printed, "owners": printed_owners}, deceased


def build_heir_cert(
    rng: random.Random, khatian: KhatianData, deceased: dict
) -> tuple[HeirCertData, dict]:
    loc = khatian.location
    issue = deceased["date_of_death"] + timedelta(days=rng.randint(200, 1500))
    if rng.random() < 0.7:
        union_no = to_bn(str(rng.randint(1, 12)))
        authority, title = f"{union_no} নং {loc.mouza} ইউনিয়ন পরিষদ", "চেয়ারম্যান"
    else:
        authority, title = f"{loc.upazila} পৌরসভা", "মেয়র"
    certificate_no = f"{rng.randint(1, 999)}/{issue.year}"

    heirs = []
    for o in khatian.owners:
        if o.relation_marker == "husband":
            relation = "wife"
        else:
            relation = "daughter" if is_female(o.name_normalized) else "son"
        heirs.append(
            {
                "name": o.name,
                "name_normalized": o.name_normalized,
                "father_or_husband_name": deceased["name"],
                "relation": relation,
                "relation_text": RELATION_TEXT[relation],
            }
        )

    cert = HeirCertData.model_validate(
        {
            "doc_type": "heir_cert",
            "certificate_no": certificate_no,
            "issue_date": issue,
            "issuing_authority": authority,
            "issuer_title": title,
            "deceased_name": deceased["name"],
            "deceased_father_or_husband_name": deceased["father"],
            "deceased_address": {
                "district": loc.district,
                "upazila": loc.upazila,
                "address_text": f"গ্রাম- {loc.mouza}",
            },
            "date_of_death": deceased["date_of_death"],
            "date_of_death_text": date_text(deceased["date_of_death"]),
            "heirs": heirs,
        }
    )
    printed = {
        "authority": authority,
        "issuer_title": title,
        "upazila": loc.upazila,
        "district": loc.district,
        "mouza": loc.mouza,
        "certificate_no": to_bn(certificate_no),
        "issue_date_text": date_text(issue),
        "deceased_name": deceased["name"],
        "deceased_father": deceased["father"],
        "date_of_death_text": cert.date_of_death_text,
        "heirs": [
            {"serial": to_bn(str(i)), "name": h["name"], "relation_text": h["relation_text"]}
            for i, h in enumerate(heirs, 1)
        ],
    }
    return cert, printed
