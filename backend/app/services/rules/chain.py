"""Ownership chain: from the older khatian, through prior deeds and inheritance, to today
(spec: docs/specs/rules.md). Conservative: a link that cannot be checked is skipped, not broken.
"""

from datetime import date

from app.schemas.land_case import SURVEY_RANK, CaseDocument, LandCase, deed_date, ref
from app.services.normalize import normalize_name
from app.services.rules.base import Rule, RuleResult, register
from app.services.rules.common import ident, person
from app.services.rules.names import names_match


def _is_owner(name: str, khatian: CaseDocument) -> bool:
    return any(names_match(name, person(o))[0] for o in khatian.data.owners)


def _newer_than(deed: CaseDocument, khatian: CaseDocument) -> bool:
    """True if the deed is after the khatian's record date, or either date is unknown."""
    record = khatian.data.record_date
    when = deed_date(deed.data)
    return record is None or when == date.min or when > record


def _year(doc: CaseDocument) -> int | None:
    d = doc.data
    for value in (
        getattr(d, "registration_date", None),
        getattr(d, "record_date", None),
        getattr(d, "date_of_death", None),
        getattr(d, "order_date", None),
    ):
        if value:
            return value.year
    year = getattr(d, "deed_year", None)
    return int(year) if year and year.isdigit() else None


def _owner_refs(khatian: CaseDocument):
    return [ref(khatian, f"owners[{j}].name_normalized") for j in range(len(khatian.data.owners))]


@register
class OwnershipChain(Rule):
    id = "ownership_chain"
    group = "chain"
    version = "1"
    codes = ("chain_break",)
    description = (
        "The predecessor of today's owners (heir certificate's deceased, else the newest prior "
        "deed's buyer) owns the source khatian or bought from its owners; every prior deed's "
        "seller owns that khatian or an older one."
    )

    def check(self, case: LandCase) -> list[RuleResult]:
        heir_cert = case.heir_certs[0] if case.heir_certs else None
        priors = case.prior_deeds  # newest first
        if heir_cert is not None and heir_cert.data.deceased_name:
            predecessor = heir_cert.data.deceased_name
            p_doc, p_ref = heir_cert, ref(heir_cert, "deceased_name")
        elif priors and priors[0].data.buyers:
            predecessor = priors[0].data.buyers[0].name
            p_doc, p_ref = priors[0], ref(priors[0], "buyers[0].name_normalized")
        else:
            return [self.skipped("ওয়ারিশ সনদ বা বায়া দলিল কেসে নেই, তাই আগের মালিক জানা যায়নি।")]
        older = case.older_khatians  # newest survey first
        if not older:
            return [self.skipped("পুরোনো খতিয়ান কেসে নেই, তাই মালিকানার ধারা মেলানো যায়নি।")]

        old_no = ident(case.mutations[0].data.old_khatian_no) if case.mutations else ""
        source = next((k for k in older if old_no and ident(k.data.khatian_no) == old_no), older[0])
        rank = SURVEY_RANK[source.data.survey_type]
        earlier = [k for k in older if SURVEY_RANK[k.data.survey_type] <= rank]  # incl. source

        breaks: list[RuleResult] = []
        pred_key = normalize_name(predecessor)  # a bare printed name
        bought = [
            d for d in priors
            if any(names_match(pred_key, person(b))[0] for b in d.data.buyers)
            and _newer_than(d, source)
        ]  # fmt: skip
        if not _is_owner(pred_key, source) and not bought:
            breaks.append(self._break(source, p_doc, predecessor, [*_owner_refs(source), p_ref]))

        for deed in priors:
            sellers = deed.data.sellers
            if not sellers:
                continue  # link cannot be checked
            missing = [s for s in sellers if not any(_is_owner(person(s), k) for k in earlier)]
            if missing:
                sources = [
                    *(r for k in earlier for r in _owner_refs(k)),
                    *(ref(deed, f"sellers[{sellers.index(s)}].name_normalized") for s in missing),
                ]
                names = "বিক্রেতা " + ", ".join(s.name for s in missing)
                breaks.append(self._break(source, deed, names, sources, earlier))
        if breaks:
            return breaks
        return [self._pass(case, earlier, priors, heir_cert)]

    def _break(self, source, to_doc, who, sources, khatians=None) -> RuleResult:
        khatians = khatians or [source]
        owners = [o.name for k in khatians for o in k.data.owners]
        values = {
            "from_document": source.label_bn,
            "owners": list(dict.fromkeys(owners)),
            "to_document": to_doc.label_bn,
            "person": who,
        }
        return self.finding("chain_break", values, sources)

    def _pass(self, case, earlier, priors, heir_cert) -> RuleResult:
        chain = [
            *sorted(earlier, key=lambda k: SURVEY_RANK[k.data.survey_type]),
            *reversed(priors),
            *([heir_cert] if heir_cert else []),
            *case.mutations,
            *([case.current_khatian] if case.current_khatian else []),
        ]
        years = [y for y in (_year(d) for d in chain) if y]
        values = {
            "earliest_year": min(years) if years else "প্রথম রেকর্ড",
            "links": " → ".join(d.label_bn for d in chain),
        }
        sources = [ref(d, "doc_type") for d in chain]
        return self.passed(values, sources)
