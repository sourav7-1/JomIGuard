"""Land case: all extracted documents of one land, each with a role and source references.

Built by services/land_case.py; the rule engine (Phase 3) reads only this. No rules here.
"""

import enum
import re
import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.extracted import ExtractedDocument

SURVEY_RANK = {"CITY": 4, "BS": 4, "RS": 3, "SA": 2, "CS": 1}  # newer survey = higher


class CaseRole(enum.StrEnum):
    current_khatian = "current_khatian"
    older_khatian = "older_khatian"
    proposed_deed = "proposed_deed"
    prior_deed = "prior_deed"
    mutation = "mutation"
    heir_cert = "heir_cert"
    unknown = "unknown"


class CaseDocumentInput(BaseModel):
    """What the builder needs per document (from the DB or a scenario file)."""

    source_id: str  # document id, or the file name for scenarios
    data: ExtractedDocument
    extraction_status: str = "ok"  # "ok" | "needs_review"
    field_flags: dict[str, list[str]] = Field(default_factory=dict)


class CaseDocument(BaseModel):
    source_id: str
    doc_type: str
    role: CaseRole
    label_bn: str  # e.g. "বর্তমান খতিয়ান (BS ৮৮২)"
    data: ExtractedDocument  # normalized
    extraction_status: str
    field_flags: dict[str, list[str]] = Field(default_factory=dict)


class BuilderWarning(BaseModel):
    """A problem putting the case together (not a finding about the land)."""

    code: str  # multiple_current_khatians | multiple_proposed_deeds | document_not_read
    message_bn: str
    source_ids: list[str] = Field(default_factory=list)


class SourceRef(BaseModel):
    source_id: str
    label_bn: str
    field_path: str  # "owners[0].share_fraction"
    printed_text: str | None  # the *_text or name as printed, else the stored value


class LandCase(BaseModel):
    land_id: uuid.UUID | None = None
    documents: list[CaseDocument] = Field(default_factory=list)
    builder_warnings: list[BuilderWarning] = Field(default_factory=list)

    def with_role(self, role: CaseRole) -> list[CaseDocument]:
        return [d for d in self.documents if d.role == role]

    @property
    def current_khatian(self) -> CaseDocument | None:
        return next(iter(self.with_role(CaseRole.current_khatian)), None)

    @property
    def older_khatians(self) -> list[CaseDocument]:
        """Newest survey first."""
        older = self.with_role(CaseRole.older_khatian)
        return sorted(older, key=lambda d: SURVEY_RANK[d.data.survey_type], reverse=True)

    @property
    def proposed_deed(self) -> CaseDocument | None:
        return next(iter(self.with_role(CaseRole.proposed_deed)), None)

    @property
    def prior_deeds(self) -> list[CaseDocument]:
        """Newest first (registration date, else deed year)."""
        deeds = self.with_role(CaseRole.prior_deed)
        return sorted(deeds, key=lambda d: deed_date(d.data), reverse=True)

    @property
    def mutations(self) -> list[CaseDocument]:
        return self.with_role(CaseRole.mutation)

    @property
    def heir_certs(self) -> list[CaseDocument]:
        return self.with_role(CaseRole.heir_cert)

    @property
    def documents_by_type(self) -> dict[str, list[CaseDocument]]:
        out: dict[str, list[CaseDocument]] = {}
        for d in self.documents:
            out.setdefault(d.doc_type, []).append(d)
        return out


def deed_date(d) -> date:
    """Sort key for deed data: registration date, else 1 January of deed_year, else date.min."""
    if d.registration_date:
        return d.registration_date
    if d.deed_year and d.deed_year.isdigit():
        return date(int(d.deed_year), 1, 1)
    return date.min


# derived field -> the printed field it came from
_PRINTED = (("_shatangsho", "_text"), ("_fraction", "_text"))


def _printed_field(field: str) -> str:
    if field == "name_normalized":
        return "name"
    for suffix, printed in _PRINTED:
        if field.endswith(suffix):
            return field.removesuffix(suffix) + printed
    return field


def _get(node, step: str):
    m = re.fullmatch(r"(\w+)(?:\[(\d+)\])?", step)
    if m is None:
        raise ValueError(f"bad field path step {step!r}")
    value = getattr(node, m.group(1))
    return value[int(m.group(2))] if m.group(2) is not None else value


def ref(doc: CaseDocument, field_path: str) -> SourceRef:
    """Where a value comes from: the document and its printed text for field_path.

    For a derived field (*_shatangsho, *_fraction, name_normalized) the printed text is its
    source field (*_text, name); otherwise the stored value itself.
    """
    *parents, field = field_path.split(".")
    node = doc.data
    for step in parents:
        node = _get(node, step)
    m = re.fullmatch(r"(\w+)(\[\d+\])?", field)
    if m and m.group(2) is None:  # plain field: look up its printed sibling
        printed = getattr(node, _printed_field(field), None)
        value = printed if printed is not None else getattr(node, field)
    else:
        value = _get(node, field)
    return SourceRef(
        source_id=doc.source_id,
        label_bn=doc.label_bn,
        field_path=field_path,
        printed_text=None if value is None else str(value),
    )


# --- API bodies for lands (api/lands.py) ---


class LandIn(BaseModel):
    mouza: str
    dag_no: str
    district: str | None = None
    upazila: str | None = None
    khatian_no: str | None = None


class LandOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    district: str
    upazila: str
    mouza: str
    dag_no: str
    khatian_no: str
