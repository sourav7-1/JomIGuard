"""User corrections on extracted document data. Spec: docs/specs/fields.md."""

import copy
import re
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.orm import Session

from app.models import Document, Extraction, ExtractionStatus
from app.schemas.extracted import (
    DeedData,
    HeirCertData,
    KhatianData,
    MutationData,
)
from app.services.normalize import normalize_document, normalize_identifier

DERIVED_FIELDS = {
    "name_normalized",
    "share_fraction",
    "share_shatangsho",
    "plot_total_area_shatangsho",
    "khatian_share_fraction",
    "area_shatangsho",
    "total_area_shatangsho",
    "transferred_area_shatangsho",
}

DOC_TYPE_MODELS = {
    "khatian": KhatianData,
    "deed": DeedData,
    "dcr": MutationData,
    "heir_cert": HeirCertData,
}

IDENTIFIER_FIELDS = {
    "dag_no",
    "khatian_no",
    "old_khatian_no",
    "new_khatian_no",
    "jl_no",
    "deed_no",
    "case_no",
    "holding_no",
    "touzi_no",
    "dcr_no",
    "certificate_no",
    "mutation_case_ref",
    "book_no",
}


class EditItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    field_path: str
    value: Any = None
    remove: bool = False


class CorrectionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    edits: list[EditItem] = Field(default_factory=list)
    confirms: list[str] = Field(default_factory=list)


def _leaf_field(path: str) -> str:
    cleaned = re.sub(r"\[\d+\]", "", path)
    return cleaned.split(".")[-1]


def _set_path_value(data: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    curr = data
    for _i, part in enumerate(parts[:-1]):
        m = re.match(r"^(\w+)\[(\d+)\]$", part)
        if m:
            key, idx = m.group(1), int(m.group(2))
            if key not in curr or not isinstance(curr[key], list) or idx >= len(curr[key]):
                raise HTTPException(422, f"‘{part}’ ঘরের অবস্থান খুঁজে পাওয়া যায়নি")
            curr = curr[key][idx]
        else:
            if part not in curr or not isinstance(curr[part], dict):
                curr[part] = {}
            curr = curr[part]

    last = parts[-1]
    m_last = re.match(r"^(\w+)\[(\d+)\]$", last)
    if m_last:
        key, idx = m_last.group(1), int(m_last.group(2))
        if key not in curr or not isinstance(curr[key], list) or idx >= len(curr[key]):
            raise HTTPException(422, f"‘{last}’ ঘরের অবস্থান খুঁজে পাওয়া যায়নি")
        curr[key][idx] = value
    else:
        curr[last] = value


def _adjust_flags_for_removal(flags: dict[str, Any], list_name: str, removed_idx: int) -> None:
    prefix = f"{list_name}[{removed_idx}]"
    to_delete = [k for k in flags if k == prefix or k.startswith(f"{prefix}.")]
    for k in to_delete:
        del flags[k]

    # Shift higher indices down
    pattern = re.compile(rf"^{list_name}\[(\d+)\](.*)$")
    shifts = {}
    for k, v in list(flags.items()):
        m = pattern.match(k)
        if m:
            idx = int(m.group(1))
            if idx > removed_idx:
                new_key = f"{list_name}[{idx - 1}]{m.group(2)}"
                shifts[k] = (new_key, v)

    for old_k, (new_k, v) in shifts.items():
        del flags[old_k]
        flags[new_k] = v


def apply_corrections(
    document: Document,
    latest_extraction: Extraction,
    edits: list[EditItem],
    confirms: list[str],
    db: Session,
) -> Extraction:
    if latest_extraction.data is None:
        raise HTTPException(400, "আগের তথ্যের কোনো রেকর্ড পাওয়া যায়নি")

    doc_type = document.doc_type or latest_extraction.data.get("doc_type")
    model_cls = DOC_TYPE_MODELS.get(str(doc_type))
    if model_cls is None:
        raise HTTPException(400, f"অসমর্থিত কাগজের ধরন: {doc_type}")

    data = copy.deepcopy(latest_extraction.data)
    new_flags = copy.deepcopy(latest_extraction.field_flags or {})

    # Sort edits: removals from highest index to lowest so list positions remain stable
    removals: list[tuple[str, int, EditItem]] = []
    regular_edits: list[EditItem] = []

    for edit in edits:
        leaf = _leaf_field(edit.field_path)
        if leaf in DERIVED_FIELDS and not edit.remove:
            raise HTTPException(
                status_code=400,
                detail="এই ঘরটি স্বয়ংক্রিয়ভাবে হিসাব করা হয়, সরাসরি বদলানো যায় না",
            )

        if edit.remove:
            m = re.match(r"^(\w+)\[(\d+)\]$", edit.field_path)
            if not m:
                raise HTTPException(422, f"‘{edit.field_path}’ তালিকা থেকে বাদ দেওয়ার উপযুক্ত ঘর নয়")
            removals.append((m.group(1), int(m.group(2)), edit))
        else:
            regular_edits.append(edit)

    # Process removals highest index first
    removals.sort(key=lambda x: x[1], reverse=True)
    for list_name, idx, edit in removals:
        if list_name not in data or not isinstance(data[list_name], list):
            raise HTTPException(422, f"‘{list_name}’ কোনো তালিকা নয়")
        if idx < 0 or idx >= len(data[list_name]):
            raise HTTPException(422, f"‘{edit.field_path}’ খুঁজে পাওয়া যায়নি")
        del data[list_name][idx]
        _adjust_flags_for_removal(new_flags, list_name, idx)

    # Process regular edits and row additions
    for edit in regular_edits:
        # Check if row addition: e.g. owners[+]
        m_add = re.match(r"^(\w+)\[\+\]$", edit.field_path)
        if m_add:
            list_name = m_add.group(1)
            if list_name not in data:
                data[list_name] = []
            if not isinstance(data[list_name], list):
                raise HTTPException(422, f"‘{list_name}’ কোনো তালিকা নয়")
            row_val = edit.value if isinstance(edit.value, dict) else {}
            data[list_name].append(row_val)
            new_idx = len(data[list_name]) - 1
            new_flags[f"{list_name}[{new_idx}]"] = ["human"]
            continue

        leaf = _leaf_field(edit.field_path)
        val = edit.value

        # Identifier check
        if leaf in IDENTIFIER_FIELDS and val is not None:
            if not isinstance(val, str):
                raise HTTPException(422, f"‘{edit.field_path}’ ঘরের মান সঠিক নয়")
            val = val.strip()
            if not val:
                raise HTTPException(422, f"‘{edit.field_path}’ খালি রাখা যাবে না")
            val = normalize_identifier(val)

        _set_path_value(data, edit.field_path, val)
        new_flags[edit.field_path] = ["human"]

    # Mark confirmed fields as human
    for confirm_path in confirms:
        new_flags[confirm_path] = ["human"]

    # Validate with Pydantic
    try:
        validated_doc = model_cls.model_validate(data)
    except ValidationError as e:
        first = e.errors()[0]
        loc = ".".join(str(p) for p in first.get("loc", []))
        msg = f"‘{loc or 'ঘর'}’ ঘরের মান সঠিক নয়"
        raise HTTPException(status_code=422, detail=msg) from e

    # Run normalize
    norm_res = normalize_document(validated_doc)
    normalized_data = norm_res.doc.model_dump(mode="json")

    # Warnings from normalize
    warnings_out = [
        {"code": w.code, "field_path": w.field_path, "message_bn": w.message_bn}
        for w in norm_res.warnings
    ]

    new_extraction = Extraction(
        document_id=document.id,
        extractor="human",
        model=None,
        prompt_version=None,
        status=ExtractionStatus.ok,
        data=normalized_data,
        warnings=warnings_out,
        field_flags=new_flags,
    )
    db.add(new_extraction)

    document.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(new_extraction)
    return new_extraction
