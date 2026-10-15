"""Gather all extracted documents of one land into a LandCase and give each a role.

build_land_case() is pure (no DB). load_land_case() reads the latest extraction of every
document of a land. Builder warnings describe problems putting the case together; they are not
findings (the rule engine produces those).
"""

import uuid

from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DocStatus, Document, Extraction, ExtractionStatus
from app.schemas.extracted import ExtractedDocument
from app.schemas.land_case import (
    SURVEY_RANK,
    BuilderWarning,
    CaseDocument,
    CaseDocumentInput,
    CaseRole,
    LandCase,
    deed_date,
)
from app.services.normalize import to_bangla_digits

WARNINGS_BN = {
    "multiple_current_khatians": "সর্বশেষ জরিপের একাধিক খতিয়ান আছে; কোনটি বর্তমান খতিয়ান তা নিশ্চিত নয়।",
    "multiple_proposed_deeds": "একাধিক দলিলের খসড়া আছে; কোনটি এখনকার বিক্রির দলিল তা নিশ্চিত নয়।",
    "document_not_read": "এই কাগজটি পড়া যায়নি, তাই কেসে রাখা হয়নি।",
}
DEED_LABELS_BN = {
    "saf_kabala": "বিক্রয় দলিল",
    "heba": "হেবা দলিল",
    "dan": "দান দলিল",
    "bonton": "বণ্টন দলিল",
    "bayna": "বায়না দলিল",
    "other": "দলিল",
}
_documents = TypeAdapter(ExtractedDocument)


def _warning(code: str, source_ids: list[str]) -> BuilderWarning:
    return BuilderWarning(code=code, message_bn=WARNINGS_BN[code], source_ids=source_ids)


def _bn(value: str | None) -> str:
    return to_bangla_digits(value or "")


def _label(role: CaseRole, data) -> str:
    match role:
        case CaseRole.current_khatian:
            return f"বর্তমান খতিয়ান ({data.survey_type} {_bn(data.khatian_no)})"
        case CaseRole.older_khatian:
            return f"পুরোনো খতিয়ান ({data.survey_type} {_bn(data.khatian_no)})"
        case CaseRole.proposed_deed:
            kind = DEED_LABELS_BN[data.deed_type]
            if data.is_draft:
                return f"{kind}ের খসড়া"
            return f"{kind} (নং {_bn(data.deed_no)})" if data.deed_no else kind
        case CaseRole.prior_deed:
            if data.deed_year:
                return f"বায়া দলিল ({_bn(data.deed_year)})"
            return f"বায়া দলিল (নং {_bn(data.deed_no)})" if data.deed_no else "বায়া দলিল"
        case CaseRole.mutation:
            return f"নামজারি (কেস {_bn(data.case_no)})"
        case CaseRole.heir_cert:
            return "ওয়ারিশ সনদ"
    return "অজানা কাগজ"


def _khatian_roles(docs: list[CaseDocumentInput], warnings: list[BuilderWarning]):
    if not docs:
        return {}
    top = max(SURVEY_RANK[d.data.survey_type] for d in docs)
    newest = [d for d in docs if SURVEY_RANK[d.data.survey_type] == top]
    if len(newest) > 1:
        warnings.append(_warning("multiple_current_khatians", [d.source_id for d in newest]))
    current = newest[0].source_id  # first in input order; the warning asks the user to check
    return {
        d.source_id: CaseRole.current_khatian if d.source_id == current else CaseRole.older_khatian
        for d in docs
    }


def _deed_roles(docs: list[CaseDocumentInput], warnings: list[BuilderWarning]):
    if not docs:
        return {}
    drafts = [d for d in docs if d.data.is_draft]
    if len(drafts) > 1:
        warnings.append(_warning("multiple_proposed_deeds", [d.source_id for d in drafts]))
    if drafts:
        proposed = drafts[0].source_id
    else:  # no draft: the latest registered deed is the one being checked
        proposed = max(docs, key=lambda d: deed_date(d.data)).source_id
    return {
        d.source_id: CaseRole.proposed_deed if d.source_id == proposed else CaseRole.prior_deed
        for d in docs
    }


def build_land_case(
    documents: list[CaseDocumentInput],
    land_id: uuid.UUID | None = None,
    warnings: list[BuilderWarning] | None = None,
) -> LandCase:
    warnings = list(warnings or [])
    by_type: dict[str, list[CaseDocumentInput]] = {}
    for d in documents:
        by_type.setdefault(d.data.doc_type, []).append(d)
    roles = {
        **_khatian_roles(by_type.get("khatian", []), warnings),
        **_deed_roles(by_type.get("deed", []), warnings),
        **{d.source_id: CaseRole.mutation for d in by_type.get("dcr", [])},
        **{d.source_id: CaseRole.heir_cert for d in by_type.get("heir_cert", [])},
    }
    case_docs = []
    for d in documents:
        role = roles.get(d.source_id, CaseRole.unknown)
        case_docs.append(
            CaseDocument(
                source_id=d.source_id,
                doc_type=d.data.doc_type,
                role=role,
                label_bn=_label(role, d.data),
                data=d.data,
                extraction_status=d.extraction_status,
                field_flags=d.field_flags,
            )
        )
    return LandCase(land_id=land_id, documents=case_docs, builder_warnings=warnings)


def load_land_case(db: Session, land_id: uuid.UUID) -> LandCase:
    """The latest successful extraction of every document of the land. Documents that failed,
    or have no usable extraction yet, are listed as document_not_read."""
    docs = db.scalars(
        select(Document).where(Document.land_id == land_id).order_by(Document.created_at)
    ).all()
    inputs, not_read = [], []
    for doc in docs:
        latest = db.scalars(
            select(Extraction)
            .where(Extraction.document_id == doc.id)
            .order_by(Extraction.created_at.desc())
            .limit(1)
        ).first()
        usable = (
            doc.status != DocStatus.failed
            and latest is not None
            and latest.status != ExtractionStatus.failed
            and latest.data is not None
        )
        if not usable:
            not_read.append(str(doc.id))
            continue
        inputs.append(
            CaseDocumentInput(
                source_id=str(doc.id),
                data=_documents.validate_python(latest.data),
                extraction_status=latest.status.value,
                field_flags=latest.field_flags or {},
            )
        )
    warnings = [_warning("document_not_read", not_read)] if not_read else []
    return build_land_case(inputs, land_id=land_id, warnings=warnings)
