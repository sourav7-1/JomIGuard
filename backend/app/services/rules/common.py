"""Helpers shared by rule groups."""

from dataclasses import dataclass

from app.schemas.extracted import Owner
from app.schemas.land_case import CaseDocument, LandCase
from app.services.normalize import normalize_identifier, normalize_name
from app.services.rules.names import names_match


def ident(value: str | None) -> str:
    return normalize_identifier(value or "")


def person(p) -> str:
    """name_normalized, or the printed name normalized if the field is empty."""
    return p.name_normalized or normalize_name(p.name)


@dataclass
class SellerMatch:
    index: int  # in deed.sellers
    seller: Owner
    owner_index: int | None  # the matched owner of the current khatian, None if not decided
    candidates: list[int]  # owners whose name matches the seller's
    reason: str  # no_name_match | name | name_and_father | ambiguous_same_name

    def owner(self, khatian: CaseDocument) -> Owner | None:
        return None if self.owner_index is None else khatian.data.owners[self.owner_index]


def same_father(seller: Owner, owner: Owner) -> bool:
    father = normalize_name(seller.father_or_husband_name or "")
    return names_match(father, normalize_name(owner.father_or_husband_name or ""))[0]


def resolve_sellers(case: LandCase) -> list[SellerMatch]:
    """Each seller of the proposed deed against the owners of the current khatian.

    Name match with names_match; if several owners share the name, the father's/husband's
    name picks one. Still ambiguous (or no match) -> owner_index None.
    """
    deed, khatian = case.proposed_deed, case.current_khatian
    if deed is None or khatian is None:
        return []
    owners = khatian.data.owners
    out = []
    for i, seller in enumerate(deed.data.sellers):
        candidates = [j for j, o in enumerate(owners) if names_match(person(seller), person(o))[0]]
        if not candidates:
            out.append(SellerMatch(i, seller, None, [], "no_name_match"))
        elif len(candidates) == 1:
            out.append(SellerMatch(i, seller, candidates[0], candidates, "name"))
        else:
            by_father = [j for j in candidates if same_father(seller, owners[j])]
            if len(by_father) == 1:
                out.append(SellerMatch(i, seller, by_father[0], candidates, "name_and_father"))
            else:
                out.append(SellerMatch(i, seller, None, candidates, "ambiguous_same_name"))
    return out
