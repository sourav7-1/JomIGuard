"""Identity rules: the proposed deed against the current khatian (spec: docs/specs/rules.md).

dag numbers, khatian numbers, mouza/JL, sellers as owners, and the sellers' father/husband.
"""

from rapidfuzz import fuzz

from app.schemas.land_case import CaseDocument, CaseRole, LandCase, ref
from app.services.normalize import normalize_name
from app.services.rules.base import Rule, RuleResult, register
from app.services.rules.common import ident as _id
from app.services.rules.common import resolve_sellers, same_father
from app.services.rules.names import match_key

MOUZA_MIN = 90  # mouza names: a one-letter spelling slip in a 5+ letter name stays above this
DEED_AND_KHATIAN = (CaseRole.proposed_deed, CaseRole.current_khatian)
SAME_NAME_BN = "খতিয়ানে একই নামের একাধিক মালিক আছেন, পিতা/স্বামীর নাম দিয়েও কে বিক্রেতা তা নিশ্চিত নয়। "


@register
class PlotsOnKhatian(Rule):
    id = "plots_on_khatian"
    group = "identity"
    version = "1"
    required_roles = DEED_AND_KHATIAN
    codes = ("dag_mismatch",)
    description = "Every dag in the deed's schedule is a dag of the current khatian."

    def check(self, case: LandCase) -> list[RuleResult]:
        deed, khatian = case.proposed_deed, case.current_khatian
        dags = [_id(p.dag_no) for p in khatian.data.plots]
        plot_refs = [ref(khatian, f"plots[{j}].dag_no") for j in range(len(dags))]
        results = []
        for i, plot in enumerate(deed.data.schedule_plots):
            dag = _id(plot.dag_no)
            if not dag:
                continue
            values = {"deed_dag": dag, "khatian": khatian.label_bn, "khatian_dags": dags}
            sources = [ref(deed, f"schedule_plots[{i}].dag_no"), *plot_refs]
            if dag in dags:
                results.append(self.passed(values, sources))
            else:
                results.append(self.finding("dag_mismatch", values, sources))
        return results or [self.skipped("দলিলের তফসিলে কোনো দাগ নম্বর পড়া যায়নি।")]


@register
class KhatianRefs(Rule):
    id = "khatian_refs"
    group = "identity"
    version = "1"
    required_roles = DEED_AND_KHATIAN
    codes = ("khatian_mismatch",)
    description = (
        "Each khatian number in the deed's schedule equals the case khatian of the same survey; "
        "references to a survey with no khatian in the case are ignored."
    )

    def check(self, case: LandCase) -> list[RuleResult]:
        deed = case.proposed_deed
        by_survey: dict[str, CaseDocument] = {}
        for k in [case.current_khatian, *case.older_khatians]:
            by_survey.setdefault(k.data.survey_type, k)
        results = []
        for i, r in enumerate(deed.data.schedule_khatians):
            khatian = by_survey.get(r.survey_type)
            if khatian is None or not _id(r.khatian_no):
                continue  # no khatian of that survey in the case: nothing to compare
            values = {
                "survey": r.survey_type,
                "deed_khatian_no": _id(r.khatian_no),
                "khatian_no": _id(khatian.data.khatian_no),
                "khatian": khatian.label_bn,
                "ref": f"{r.survey_type} {_id(r.khatian_no)}",
            }
            sources = [ref(deed, f"schedule_khatians[{i}].khatian_no"), ref(khatian, "khatian_no")]
            if values["deed_khatian_no"] == values["khatian_no"]:
                results.append(self.passed(values, sources))
            else:
                results.append(self.finding("khatian_mismatch", values, sources))
        return results or [
            self.skipped("দলিলের খতিয়ান নম্বরের সাথে মেলানোর মতো একই জরিপের খতিয়ান কেসে নেই।")
        ]


@register
class MouzaMatch(Rule):
    id = "mouza_match"
    group = "identity"
    version = "1"
    required_roles = DEED_AND_KHATIAN
    codes = ("mouza_mismatch",)
    description = (
        "The deed's schedule mouza (and JL number, if both print one) equals the khatian's."
    )

    def check(self, case: LandCase) -> list[RuleResult]:
        deed, khatian = case.proposed_deed, case.current_khatian
        d_loc, k_loc = deed.data.schedule_location, khatian.data.location
        if not match_key(d_loc.mouza) or not match_key(k_loc.mouza):
            return [self.skipped("দলিল বা খতিয়ানের মৌজার নাম পড়া যায়নি।")]
        d_jl, k_jl = _id(d_loc.jl_no), _id(k_loc.jl_no)
        same_mouza = fuzz.ratio(match_key(d_loc.mouza), match_key(k_loc.mouza)) >= MOUZA_MIN
        same_jl = not (d_jl and k_jl) or d_jl == k_jl
        values = {
            "deed_mouza": d_loc.mouza,
            "khatian_mouza": k_loc.mouza,
            "deed_jl": d_jl or None,
            "khatian_jl": k_jl or None,
            "khatian": khatian.label_bn,
        }
        sources = [ref(deed, "schedule_location.mouza"), ref(khatian, "location.mouza")]
        if d_jl and k_jl:
            sources += [ref(deed, "schedule_location.jl_no"), ref(khatian, "location.jl_no")]
        if same_mouza and same_jl:
            return [self.passed(values, sources)]
        return [self.finding("mouza_mismatch", values, sources)]


@register
class SellerIsOwner(Rule):
    id = "seller_is_owner"
    group = "identity"
    version = "1"
    required_roles = DEED_AND_KHATIAN
    codes = ("seller_not_owner",)
    description = "Every deed seller matches an owner of the current khatian (names_match)."

    def check(self, case: LandCase) -> list[RuleResult]:
        deed, khatian = case.proposed_deed, case.current_khatian
        owners = khatian.data.owners
        owner_refs = [ref(khatian, f"owners[{j}].name_normalized") for j in range(len(owners))]
        results = []
        for m in resolve_sellers(case):
            seller_ref = ref(deed, f"sellers[{m.index}].name_normalized")
            values = {"seller": m.seller.name, "khatian": khatian.label_bn}
            if m.candidates:
                values["owner"] = owners[m.candidates[0]].name
                sources = [seller_ref, *(owner_refs[j] for j in m.candidates)]
                results.append(self.passed(values, sources))
            else:
                values["owners"] = [o.name for o in owners]
                results.append(self.finding("seller_not_owner", values, [seller_ref, *owner_refs]))
        return results or [self.skipped("দলিলে বিক্রেতার নাম পড়া যায়নি।")]


@register
class SellerFather(Rule):
    id = "seller_father"
    group = "identity"
    version = "1"
    required_roles = DEED_AND_KHATIAN
    codes = ("seller_father_mismatch",)
    description = (
        "For a seller who matched an owner, the father's/husband's name matches too; it also "
        "picks between owners with the same name."
    )

    def check(self, case: LandCase) -> list[RuleResult]:
        deed, khatian = case.proposed_deed, case.current_khatian
        owners = khatian.data.owners
        results = []
        for m in resolve_sellers(case):
            if not m.candidates:
                continue  # seller_is_owner reports it
            seller = m.seller
            if not normalize_name(seller.father_or_husband_name or ""):
                results.append(self.skipped(f"দলিলে বিক্রেতা {seller.name}-এর পিতা/স্বামীর নাম নেই।"))
                continue
            seller_refs = [
                ref(deed, f"sellers[{m.index}].name_normalized"),
                ref(deed, f"sellers[{m.index}].father_or_husband_name"),
            ]
            values = {
                "seller": seller.name,
                "deed_father": seller.father_or_husband_name,
                "khatian": khatian.label_bn,
                "note": "",
            }
            chosen = m.owner_index
            if chosen is not None and same_father(seller, owners[chosen]):
                values["khatian_father"] = owners[chosen].father_or_husband_name
                sources = [*seller_refs, ref(khatian, f"owners[{chosen}].father_or_husband_name")]
                results.append(self.passed(values, sources))
                continue
            khatian_fathers = [owners[j].father_or_husband_name for j in m.candidates]
            if len(m.candidates) == 1 and not khatian_fathers[0]:
                results.append(self.skipped("খতিয়ানে এই মালিকের পিতা/স্বামীর নাম নেই।"))
                continue
            values["khatian_father"] = [f for f in khatian_fathers if f] or None
            if len(m.candidates) > 1:
                values["note"] = SAME_NAME_BN
            sources = [
                *seller_refs,
                *(ref(khatian, f"owners[{j}].father_or_husband_name") for j in m.candidates),
            ]
            results.append(self.finding("seller_father_mismatch", values, sources))
        return results or [self.skipped("কোনো বিক্রেতা খতিয়ানের মালিকের সাথে মেলেনি।")]
