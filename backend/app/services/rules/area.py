"""Area rules: owners' shares add up, the sale stays within the sellers' share, and areas whose
unit could not be converted (spec: docs/specs/rules.md). Decimal throughout, no rounding.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from app.schemas.land_case import CaseDocument, CaseRole, LandCase, SourceRef, ref
from app.services.normalize import parse_area, parse_share
from app.services.rules.base import Rule, RuleResult, register
from app.services.rules.common import ident, resolve_sellers
from app.services.rules.messages import show

# Shares are printed with 3 decimals (".৩৩৪ + .৩৩৩ + .৩৩৩"): a sum within 0.001 of the whole is
# the same land split in thousandths, not a missing share.
SHARE_TOLERANCE = Decimal("0.001")
ONE = Decimal(1)
LAND_RECORDS = (CaseRole.current_khatian, CaseRole.older_khatian, CaseRole.mutation)
UNIT_CODES = ("unsupported_unit", "missing_unit")


def _sum(values) -> Decimal:
    return sum(values, Decimal(0))


def _whole_area(doc: CaseDocument) -> Decimal | None:
    """Total area in shatangsho: the printed total, else the sum of the plots' areas."""
    data = doc.data
    if data.total_area_shatangsho is not None:
        return data.total_area_shatangsho
    areas = [p.area_shatangsho for p in data.plots]
    return _sum(areas) if areas and all(a is not None for a in areas) else None


@register
class SharesAddUp(Rule):
    id = "shares_add_up"
    group = "area"
    version = "1"
    codes = ("area_sum_mismatch",)
    description = "On every khatian and mutation, the owners' shares sum to the whole."

    def check(self, case: LandCase) -> list[RuleResult]:
        docs = [d for d in case.documents if d.role in LAND_RECORDS]
        if not docs:
            return [self.skipped("কেসে কোনো খতিয়ান বা নামজারি নেই।")]
        return [self._one(doc) for doc in docs]

    def _one(self, doc: CaseDocument) -> RuleResult:
        owners = doc.data.owners
        whole = _whole_area(doc)
        area = {
            "whole_shatangsho": whole,
            "whole_text": f"পুরো {show(whole)} শতাংশ" if whole is not None else "পুরো জমি",
        }
        printed = [o for o in owners if o.share_text]
        if printed and any(o.share_fraction is None for o in printed):
            return self.skipped(f"{doc.label_bn}-এ কোনো মালিকের অংশ পড়া যায়নি।")
        if printed and len(printed) == len(owners):
            total = _sum(o.share_fraction for o in owners)
            values = {"document": doc.label_bn, "total_shares": total, "expected": ONE,
                      "unit": "", "method": "fraction", **area}  # fmt: skip
            ok = abs(total - ONE) <= SHARE_TOLERANCE
            sources = [ref(doc, f"owners[{j}].share_fraction") for j in range(len(owners))]
        else:
            areas = [o.share_shatangsho for o in owners]
            if whole is None or not owners or any(a is None for a in areas):
                return self.skipped(f"{doc.label_bn}-এ মালিকদের অংশ বা মোট জমি পড়া যায়নি।")
            total = _sum(areas)
            values = {"document": doc.label_bn, "total_shares": total, "expected": whole,
                      "unit": " শতাংশ", "method": "shatangsho", **area}  # fmt: skip
            ok = abs(total - whole) <= SHARE_TOLERANCE * whole
            sources = [ref(doc, "total_area_shatangsho")]
        if ok:
            return self.passed(values, sources)
        return self.finding("area_sum_mismatch", values, sources)


@dataclass
class SalePart:
    """One comparison: the sellers' area vs the area sold (one dag, or a total)."""

    method: str  # per_dag | total_over_listed_dags | whole_khatian
    dags: list[str]
    available: Decimal
    sold: Decimal
    sources: list[SourceRef]
    scope: str  # Bangla, e.g. " দাগ ৩০৫-এ"

    @property
    def shortfall(self) -> Decimal:
        return max(self.sold - self.available, Decimal(0))


@dataclass
class SaleCheck:
    """compute_sale_vs_share() result. method None = could not compute (skip_reason says why)."""

    method: str | None = None
    parts: list[SalePart] = field(default_factory=list)
    sellers: list[str] = field(default_factory=list)
    seller_owners: list[int] = field(default_factory=list)  # matched owner indices
    skip_reason: str | None = None

    @property
    def available(self) -> Decimal:
        return _sum(p.available for p in self.parts)

    @property
    def sold(self) -> Decimal:
        return _sum(p.sold for p in self.parts)

    @property
    def shortfall(self) -> Decimal:
        return _sum(p.shortfall for p in self.parts)

    @property
    def dags(self) -> list[str]:
        return [d for p in self.parts for d in p.dags]


def compute_sale_vs_share(case: LandCase) -> SaleCheck:
    """Area the proposed deed transfers vs the sellers' area on the current khatian (pure).

    Owner area in a plot = share_fraction x plot area (Decision 3, needs expert check).
    Per dag when every schedule dag is on the current khatian (total over the listed dags if
    the deed gives no per-dag area); otherwise the sellers' share of the whole khatian.
    """
    deed, khatian = case.proposed_deed, case.current_khatian
    if deed is None or khatian is None:
        return SaleCheck(skip_reason="দলিল বা বর্তমান খতিয়ান কেসে নেই।")
    matches = resolve_sellers(case)
    if not matches:
        return SaleCheck(skip_reason="দলিলে বিক্রেতার নাম পড়া যায়নি।")
    sellers = [m.seller.name for m in matches]
    unmatched = [m.seller.name for m in matches if m.owner_index is None]
    if unmatched:
        names = ", ".join(unmatched)
        return SaleCheck(
            sellers=sellers,
            skip_reason=f"বিক্রেতা {names} খতিয়ানের মালিকের সাথে মেলেনি, তাই অংশ হিসাব করা যায়নি।",
        )
    owners = list(dict.fromkeys(m.owner_index for m in matches))  # same owner once
    base = SaleCheck(sellers=sellers, seller_owners=owners)
    if deed.data.transferred_area_shatangsho is None:
        base.skip_reason = "দলিলের হস্তান্তরিত জমির পরিমাণ শতাংশে পড়া যায়নি।"
        return base
    fractions = [khatian.data.owners[j].share_fraction for j in owners]
    if any(f is None for f in fractions):
        base.skip_reason = "খতিয়ানে বিক্রেতার অংশ পড়া যায়নি।"
        return base

    owner_refs = [ref(khatian, f"owners[{j}].share_fraction") for j in owners]
    plots = {ident(p.dag_no): (n, p) for n, p in enumerate(khatian.data.plots)}
    schedule = [(i, ident(p.dag_no), p) for i, p in enumerate(deed.data.schedule_plots)]
    schedule = [s for s in schedule if s[1]]
    transferred = deed.data.transferred_area_shatangsho
    transferred_ref = ref(deed, "transferred_area_shatangsho")

    if schedule and all(dag in plots for _, dag, _ in schedule):
        missing = [dag for _, dag, _ in schedule if plots[dag][1].area_shatangsho is None]
        if missing:
            base.skip_reason = f"খতিয়ানে দাগ {', '.join(missing)}-এর জমির পরিমাণ পড়া যায়নি।"
            return base

        def available(dag: str) -> Decimal:
            return _sum(f * plots[dag][1].area_shatangsho for f in fractions)

        def plot_ref(dag: str) -> SourceRef:
            return ref(khatian, f"plots[{plots[dag][0]}].area_shatangsho")

        if all(p.area_shatangsho is not None for _, _, p in schedule):  # area per dag
            base.method = "per_dag"
            base.parts = [
                SalePart(
                    "per_dag",
                    [dag],
                    available(dag),
                    p.area_shatangsho,
                    [*owner_refs, plot_ref(dag), ref(deed, f"schedule_plots[{i}].area_shatangsho")],
                    f" দাগ {dag}-এ",
                )  # fmt: skip
                for i, dag, p in schedule
            ]
            return base
        dags = [dag for _, dag, _ in schedule]
        base.method = "total_over_listed_dags"
        base.parts = [
            SalePart(
                "total_over_listed_dags",
                dags,
                _sum(available(d) for d in dags),
                transferred,
                [*owner_refs, *(plot_ref(d) for d in dags), transferred_ref],
                f" দাগ {', '.join(dags)}-এ",
            )  # fmt: skip
        ]
        return base

    # a schedule dag is not on the current khatian (or none was read): whole khatian
    shares = [khatian.data.owners[j].share_shatangsho for j in owners]
    if any(s is None for s in shares):
        base.skip_reason = "খতিয়ানে বিক্রেতার অংশের জমির পরিমাণ পড়া যায়নি।"
        return base
    base.method = "whole_khatian"
    base.parts = [
        SalePart(
            "whole_khatian",
            [dag for _, dag, _ in schedule],
            _sum(shares),
            transferred,
            [*owner_refs, transferred_ref],
            "",
        )  # fmt: skip
    ]
    return base


@register
class SoldWithinShare(Rule):
    id = "sold_within_share"
    group = "area"
    version = "1"
    required_roles = (CaseRole.proposed_deed, CaseRole.current_khatian)
    codes = ("area_exceeds_share",)
    description = (
        "The area the deed transfers is at most the sellers' share on the current khatian: per "
        "dag (share_fraction x plot area) when every schedule dag is on the khatian, else the "
        "sellers' share of the whole khatian."
    )

    def check(self, case: LandCase) -> list[RuleResult]:
        sale = compute_sale_vs_share(case)
        if sale.method is None:
            return [self.skipped(sale.skip_reason)]
        common = {
            "sellers": sale.sellers,
            "seller_names": " ও ".join(sale.sellers),
            "share_label": "অংশ" if len(sale.seller_owners) == 1 else "মোট অংশ",
        }
        return [self._compare(common, part) for part in sale.parts]

    def _compare(self, common: dict, part: SalePart) -> RuleResult:
        values = {**common, "method": part.method, "dags": part.dags, "scope": part.scope,
                  "available_shatangsho": part.available, "sold_shatangsho": part.sold,
                  "share": part.available, "transferred": part.sold,
                  "excess": part.sold - part.available}  # fmt: skip
        if part.sold > part.available:
            return self.finding("area_exceeds_share", values, part.sources)
        return self.passed(values, part.sources)


# (container attribute, text field, derived field, kind)
_PLOT_FIELDS = (
    ("plot_total_area_text", "plot_total_area_shatangsho", "area"),
    ("khatian_share_text", "khatian_share_fraction", "share"),
    ("area_text", "area_shatangsho", "area"),
)
_PERSON_FIELDS = (("share_text", "share_fraction", "share"),)


def _fields(data):
    """(path, text, derived, kind) for every area/share field of a document."""
    lists = {
        "plots": _PLOT_FIELDS,
        "schedule_plots": _PLOT_FIELDS,
        "owners": _PERSON_FIELDS,
        "sellers": _PERSON_FIELDS,
        "buyers": _PERSON_FIELDS,
        "heirs": _PERSON_FIELDS,
    }
    for name, fields in lists.items():
        for i, item in enumerate(getattr(data, name, None) or []):
            for text, derived, kind in fields:
                yield f"{name}[{i}].{text}", getattr(item, text), getattr(item, derived), kind
    for text, derived in (("total_area_text", "total_area_shatangsho"),
                          ("transferred_area_text", "transferred_area_shatangsho")):  # fmt: skip
        if hasattr(data, text):
            yield text, getattr(data, text), getattr(data, derived), "area"


@register
class Units(Rule):
    id = "units"
    group = "area"
    version = "1"
    codes = UNIT_CODES
    description = (
        "Areas and shares printed but not converted: unsupported unit (বিঘা, কাঠা, আনা ...) or no "
        "unit in the cell or column header. One finding per document and code."
    )

    def check(self, case: LandCase) -> list[RuleResult]:
        results = []
        for doc in case.documents:
            hint = getattr(doc.data, "area_unit_text", None)
            problems: dict[str, list[tuple[str, str]]] = {}
            for path, text, derived, kind in _fields(doc.data):
                if not text or derived is not None:
                    continue
                code = parse_area(text, hint)[1] if kind == "area" else parse_share(text)[1]
                if code in UNIT_CODES:
                    problems.setdefault(code, []).append((path, text))
            for code, items in problems.items():
                values = {
                    "document": doc.label_bn,
                    "fields": [p for p, _ in items],
                    "printed": list(dict.fromkeys(t for _, t in items)),
                }
                sources = [ref(doc, p) for p, _ in items]
                results.append(self.finding(code, values, sources))
        if results:
            return results
        return [self.passed({}, [])]
