"""Completeness rules: documents the case relies on but does not contain."""

from app.schemas.land_case import CaseRole, LandCase, ref
from app.services.normalize import clean
from app.services.rules.base import Rule, RuleResult, register

INHERITANCE = "ওয়ারিশ"


@register
class TitleDocuments(Rule):
    """A deed whose title says the seller inherited the land needs an heir certificate."""

    id = "title_documents"
    group = "completeness"
    version = "1"
    required_roles = (CaseRole.proposed_deed,)
    codes = ("document_missing",)
    description = (
        "document_missing when the proposed deed's title_source_text says ওয়ারিশ (inheritance) "
        "and the case has no heir certificate (findings.md)."
    )

    def check(self, case: LandCase) -> list[RuleResult]:
        deed = case.proposed_deed
        title = deed.data.title_source_text
        if not title:
            return [self.skipped("দলিলে মালিকানার সূত্র পড়া যায়নি, তাই যাচাই করা যায়নি।")]
        source = [ref(deed, "title_source_text")]
        values = {"title_source_text": title}
        if INHERITANCE in clean(title) and not case.heir_certs:
            missing = {"missing_document": "ওয়ারিশ সনদ", "missing_role": "heir_cert"}
            return [self.finding("document_missing", {**values, **missing}, source)]
        return [self.passed(values, source)]
