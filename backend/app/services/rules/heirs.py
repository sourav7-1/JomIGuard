"""Heirs rules: co-owners' consent when a sale exceeds the sellers' share, and heirs missing
from the mutation (spec: docs/specs/rules.md). Conservative: when unsure, skip with a reason.

No inheritance shares are computed here (Decision 5): shares come from the khatian / mutation.
"""

from app.schemas.land_case import CaseDocument, CaseRole, LandCase, ref
from app.services.normalize import clean
from app.services.rules.area import compute_sale_vs_share
from app.services.rules.base import Rule, RuleResult, register
from app.services.rules.common import person
from app.services.rules.names import names_match

INHERITANCE = "ওয়ারিশ"
DAG_METHODS = ("per_dag", "total_over_listed_dags")  # the sold dags are on the current khatian


def _heir_index(heir_cert: CaseDocument, owner) -> int | None:
    for i, heir in enumerate(heir_cert.data.heirs):
        if names_match(person(owner), person(heir))[0]:
            return i
    return None


@register
class CoOwnerConsent(Rule):
    id = "co_owner_consent"
    group = "heirs"
    version = "1"
    required_roles = (CaseRole.proposed_deed, CaseRole.current_khatian)
    codes = ("heir_consent_missing",)
    description = (
        "When the deed transfers more than the sellers own in the sold dags, the co-heirs who "
        "own the rest must be sellers on the deed (no other consent document is recognised)."
    )

    def check(self, case: LandCase) -> list[RuleResult]:
        sale = compute_sale_vs_share(case)
        if sale.method is None:
            return [self.skipped(sale.skip_reason)]
        if sale.method not in DAG_METHODS:
            return [
                self.skipped("দলিলের দাগ বর্তমান খতিয়ানে নেই, তাই বাকি জমি কার অংশ থেকে আসছে তা বলা যায় না।")
            ]
        if sale.shortfall <= 0:
            return [self.passed({"shortfall": sale.shortfall}, [])]

        deed, khatian = case.proposed_deed, case.current_khatian
        owners = khatian.data.owners
        co_owners = [j for j in range(len(owners)) if j not in sale.seller_owners]
        if not co_owners:
            return [self.skipped("খতিয়ানে বিক্রেতারা ছাড়া অন্য কোনো মালিক নেই।")]

        heir_cert = case.heir_certs[0] if case.heir_certs else None
        title = deed.data.title_source_text or ""
        if heir_cert is not None:
            heir_of = {j: _heir_index(heir_cert, owners[j]) for j in co_owners}
            co_heirs = [j for j in co_owners if heir_of[j] is not None]
            heir_sources = [
                ref(heir_cert, f"heirs[{heir_of[j]}].name_normalized") for j in co_heirs
            ]
        elif INHERITANCE in clean(title):
            co_heirs = co_owners
            heir_sources = [ref(deed, "title_source_text")]
        else:
            return [self.skipped("অন্য অংশীদাররা ওয়ারিশ কিনা কাগজে জানা যায়নি।")]
        if not co_heirs:
            return [self.skipped("অন্য অংশীদাররা ওয়ারিশ সনদে নেই।")]

        # consent counts only if the co-heir also sells on this deed (they do not: not matched)
        names = [owners[j].name for j in co_heirs]
        values = {
            "shortfall": sale.shortfall,
            "co_owners": names,
            "co_owner_names": " বা ".join(names),
            "co_owner_shares": {owners[j].name: owners[j].share_text for j in co_heirs},
            "dags": sale.dags,
        }
        seller_sources = [
            ref(deed, f"sellers[{i}].name_normalized") for i in range(len(deed.data.sellers))
        ]
        # the co-owners' shares come from the current khatian
        share_sources = [ref(khatian, f"owners[{j}].share_fraction") for j in co_heirs]
        sources = [*seller_sources, *share_sources, *heir_sources]
        return [self.finding("heir_consent_missing", values, sources)]


@register
class HeirsInMutation(Rule):
    id = "heirs_in_mutation"
    group = "heirs"
    version = "1"
    required_roles = (CaseRole.heir_cert,)
    codes = ("heir_missing_from_mutation",)
    description = (
        "Every living heir on the heir certificate is an owner of the mutation (or of the "
        "current khatian if there is no mutation)."
    )

    def check(self, case: LandCase) -> list[RuleResult]:
        record = case.mutations[0] if case.mutations else case.current_khatian
        if record is None:
            return [self.skipped("ওয়ারিশদের মেলানোর জন্য নামজারি বা বর্তমান খতিয়ান কেসে নেই।")]
        heir_cert = case.heir_certs[0]
        owners = record.data.owners
        deceased = [h.name for h in heir_cert.data.heirs if h.is_deceased]
        note = f" (মৃত হিসাবে চিহ্নিত, তাই বাদ: {', '.join(deceased)})" if deceased else ""
        results = []
        for i, heir in enumerate(heir_cert.data.heirs):
            if heir.is_deceased:
                continue
            match = next(
                (j for j, o in enumerate(owners) if names_match(person(heir), person(o))[0]), None
            )
            values = {"heir": heir.name, "record": record.label_bn, "deceased_note": note,
                      "skipped_deceased": deceased}  # fmt: skip
            heir_ref = ref(heir_cert, f"heirs[{i}].name_normalized")
            if match is None:
                owner_refs = [
                    ref(record, f"owners[{j}].name_normalized") for j in range(len(owners))
                ]
                results.append(
                    self.finding("heir_missing_from_mutation", values, [heir_ref, *owner_refs])
                )
            else:
                values["owner"] = owners[match].name
                owner_ref = ref(record, f"owners[{match}].name_normalized")
                results.append(self.passed(values, [heir_ref, owner_ref]))
        return results or [self.skipped("ওয়ারিশ সনদে কোনো জীবিত ওয়ারিশ নেই।")]
