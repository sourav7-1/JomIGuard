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
    doc_bn: str = ""  # where, for people: "খতিয়ানে", "দলিলে", "নামজারিতে", "ওয়ারিশ সনদে"
    value_bn: str = ""  # the labelled value: "রহিম উদ্দিনের অংশ .৪০০", "দাগ ৩০৫-এ জমি .১৫০০ একর"


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
    printed = None if value is None else str(value)
    return SourceRef(
        source_id=doc.source_id,
        label_bn=doc.label_bn,
        field_path=field_path,
        printed_text=printed,
        doc_bn=DOC_IN_BN.get(doc.doc_type, ""),
        value_bn=_value_bn(doc, parents, _printed_field(m.group(1)) if m else field, printed),
    )


# --- labelled values for people (report "লেখা আছে", case page) ---

DOC_IN_BN = {"khatian": "খতিয়ানে", "dcr": "নামজারিতে", "deed": "দলিলে", "heir_cert": "ওয়ারিশ সনদে"}
_ROLE_BN = {"owners": "মালিক", "sellers": "বিক্রেতা", "buyers": "ক্রেতা", "heirs": "ওয়ারিশ"}
_AREA_FIELDS = ("area_text", "plot_total_area_text", "total_area_text")
_VOWEL_SIGNS = "ািীুূৃেৈোৌ"
_BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")


def genitive_bn(name: str) -> str:
    """ "রহিম উদ্দিন" -> "রহিম উদ্দিনের", "রুনা" -> "রুনার"."""
    name = name.strip()
    return f"{name}র" if name and name[-1] in _VOWEL_SIGNS else f"{name}ের"


def _value_bn(doc: CaseDocument, parents: list[str], field: str, printed: str | None) -> str:
    if printed is None or field == "doc_type":
        return ""
    data = doc.data
    item, list_name = None, None
    if parents:
        m = re.fullmatch(r"(\w+)\[(\d+)\]", parents[-1])
        if m:
            list_name, item = m.group(1), _get(data, parents[-1])
    unit = getattr(data, "area_unit_text", None)
    if field in _AREA_FIELDS and unit and unit not in printed:
        printed = f"{printed} {unit}"
    person = getattr(item, "name", None) if list_name in _ROLE_BN else None
    dag = getattr(item, "dag_no", None) if list_name in ("plots", "schedule_plots") else None
    if field == "name":
        text = f"{_ROLE_BN[list_name]} {printed}" if list_name in _ROLE_BN else printed
    elif person and field == "share_text":
        text = f"{genitive_bn(person)} অংশ {printed}"
    elif person and field == "father_or_husband_name":
        text = f"{genitive_bn(person)} পিতা/স্বামী {printed}"
    elif dag and field == "area_text":
        text = f"দাগ {dag}-এ {'জমি ' if list_name == 'plots' else ''}{printed}"
    elif dag and field == "plot_total_area_text":
        text = f"দাগ {dag}-এর মোট জমি {printed}"
    elif dag and field == "khatian_share_text":
        text = f"দাগ {dag}-এ খতিয়ানের অংশ {printed}"
    elif field == "dag_no":
        text = f"দাগ নং {printed}"
    elif list_name == "schedule_khatians" and field == "khatian_no":
        text = f"খতিয়ান নং {item.survey_type} {printed}"
    elif field in ("khatian_no", "new_khatian_no", "old_khatian_no"):
        survey = getattr(data, "survey_type", "")
        text = f"খতিয়ান নং {survey} {printed}".replace("  ", " ")
    elif field == "total_area_text":
        text = f"মোট জমি {printed}"
    elif field == "transferred_area_text":
        text = printed
    elif field == "mouza":
        text = f"মৌজা {printed}"
    elif field == "jl_no":
        text = f"জে.এল. নং {printed}"
    elif field == "title_source_text":
        text = f'মালিকানার সূত্র "{printed}"'
    elif field == "deceased_name":
        text = f"মৃত {printed}"
    else:
        text = printed
    return text.translate(_BN_DIGITS)


def describe_sources(sources: list[SourceRef]) -> str:
    """ "খতিয়ানে রহিম উদ্দিনের অংশ .৪০০ · দাগ ৩০৫-এ জমি .১৫০০ একর · দলিলে ১০ শতাংশ":
    the document is named only when it changes; duplicates are dropped."""
    parts, last_doc, seen = [], None, set()
    for s in sources:
        if not s.value_bn or (s.source_id, s.value_bn) in seen:
            continue
        seen.add((s.source_id, s.value_bn))
        prefix = f"{s.doc_bn} " if s.source_id != last_doc and s.doc_bn else ""
        parts.append(prefix + s.value_bn)
        last_doc = s.source_id
    return " · ".join(parts)


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
