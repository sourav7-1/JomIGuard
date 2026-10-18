from app.schemas.land_case import CaseRole, LandCase, ref
from app.services.rules.base import Rule, RuleResult, register
from app.services.rules.common import resolve_sellers
from app.services.rules.names import names_match


@register
class SellerIdentity(Rule):
    id = "seller_identity"
    group = "identity"
    version = "1"
    required_roles = (CaseRole.proposed_deed, CaseRole.current_khatian)
    codes = ("seller_identity_unverified", "seller_nid_name_mismatch")
    description = (
        "A database-backed seller identity result matches the deed seller and khatian owner."
    )

    def check(self, case: LandCase) -> list[RuleResult]:
        if case.identity is None:
            return [self.skipped("এই scenario-তে পরিচয় যাচাইয়ের ফল নেই।")]

        deed, khatian = case.proposed_deed, case.current_khatian
        results = []
        for match in resolve_sellers(case):
            seller = match.seller
            saved = [
                item
                for item in case.identity
                if item.seller_name_on_deed
                and names_match(item.seller_name_on_deed, seller.name)[0]
            ]
            latest = saved[-1] if saved else None
            if latest is None or latest.status != "verified" or not latest.name_bn_as_per_nid:
                results.append(
                    self.finding(
                        "seller_identity_unverified",
                        {"seller": seller.name},
                        [ref(deed, f"sellers[{match.index}].name_normalized")],
                    )
                )
                continue

            name_matches_seller = names_match(latest.name_bn_as_per_nid, seller.name)[0]
            name_matches_owner = any(
                names_match(latest.name_bn_as_per_nid, khatian.data.owners[i].name)[0]
                for i in match.candidates
            )
            father_mismatch = False
            if latest.father_name_as_per_nid:
                owner_fathers = [
                    khatian.data.owners[i].father_or_husband_name for i in match.candidates
                ]
                if seller.father_or_husband_name:
                    father_mismatch = not names_match(
                        latest.father_name_as_per_nid, seller.father_or_husband_name
                    )[0]
                if owner_fathers and any(owner_fathers):
                    father_mismatch = father_mismatch or not any(
                        father and names_match(latest.father_name_as_per_nid, father)[0]
                        for father in owner_fathers
                    )

            sources = [
                ref(deed, f"sellers[{match.index}].name_normalized"),
                *(ref(khatian, f"owners[{i}].name_normalized") for i in match.candidates),
            ]
            values = {"seller": seller.name, "verified_name": latest.name_bn_as_per_nid}
            if name_matches_seller and name_matches_owner and not father_mismatch:
                results.append(self.passed(values, sources))
            else:
                results.append(self.finding("seller_nid_name_mismatch", values, sources))
        return results or [self.skipped("দলিলে বিক্রেতার নাম পাওয়া যায়নি।")]
