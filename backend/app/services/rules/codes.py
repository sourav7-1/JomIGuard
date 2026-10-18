"""Finding codes: the vocabulary of docs/specs/findings.md (a test keeps the two in sync)."""

from dataclasses import dataclass

GROUP_ORDER = ("identity", "area", "heirs", "chain", "completeness")


@dataclass(frozen=True)
class Code:
    code: str
    group: str
    severity: str  # "bad" | "warn"


CODES: dict[str, Code] = {
    c.code: c
    for c in (
        Code("dag_mismatch", "identity", "bad"),
        Code("khatian_mismatch", "identity", "bad"),
        Code("mouza_mismatch", "identity", "bad"),
        Code("seller_not_owner", "identity", "bad"),
        Code("seller_father_mismatch", "identity", "warn"),
        Code("seller_identity_unverified", "identity", "warn"),
        Code("seller_nid_name_mismatch", "identity", "bad"),
        Code("area_exceeds_share", "area", "bad"),
        Code("area_sum_mismatch", "area", "warn"),
        Code("unsupported_unit", "area", "warn"),
        Code("missing_unit", "area", "warn"),
        Code("heir_consent_missing", "heirs", "warn"),
        Code("heir_missing_from_mutation", "heirs", "warn"),
        Code("chain_break", "chain", "bad"),
        Code("document_missing", "completeness", "warn"),
    )
}
