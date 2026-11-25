from app.schemas.land_case import CaseRole, LandCase, ref
from app.services.rules import messages
from app.services.rules.base import Rule, RuleResult, Status, register
from app.services.rules.common import resolve_sellers
from app.services.rules.names import names_match, nid_match


@register
class SellerIdentity(Rule):
    id = "seller_identity"
    group = "identity"
    version = "2"  # 2: partial result (seller_nid_name_partial), OCR-read names
    required_roles = (CaseRole.proposed_deed, CaseRole.current_khatian)
    codes = ("seller_identity_unverified", "seller_nid_name_mismatch", "seller_nid_name_partial")
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

            result, score = nid_match(
                latest.name_bn_as_per_nid,
                latest.father_name_as_per_nid,
                [(seller.name, seller.father_or_husband_name)],
                [(khatian.data.owners[i].name, khatian.data.owners[i].father_or_husband_name)
                 for i in match.candidates],
            )  # fmt: skip
            sources = [
                ref(deed, f"sellers[{match.index}].name_normalized"),
                *(ref(khatian, f"owners[{i}].name_normalized") for i in match.candidates),
            ]
            values = {
                "seller": seller.name,
                "verified_name": latest.name_bn_as_per_nid,
                "match_result": result,
                "score": score,
            }
            if result == "matched":
                results.append(self.passed(values, sources))
                continue
            code = "seller_nid_name_partial" if result == "partial" else "seller_nid_name_mismatch"
            found = self.finding(code, values, sources)
            if latest.name_source == "ocr":  # limited read: check by hand, never a mismatch
                found = _to_verify(found)
            results.append(found)
        return results or [self.skipped("দলিলে বিক্রেতার নাম পাওয়া যায়নি।")]


def _to_verify(found: RuleResult) -> RuleResult:
    """An OCR-read NID name: listed under "যাচাই করা যায়নি / মিলিয়ে নিন" (RuleRun.to_verify)."""
    reason = messages.OCR_NID_BN.format(message=found.message_bn)
    values = {**found.values, "ocr_read": True, "ocr_original_code": found.code,
              "ocr_original_title": found.title_bn}  # fmt: skip
    return found.model_copy(update={
        "code": None, "status": Status.skipped, "title_bn": messages.OCR_UNVERIFIED_TITLE,
        "message_bn": reason, "skip_reason": reason, "values": values,
    })  # fmt: skip
