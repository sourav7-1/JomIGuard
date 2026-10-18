import re
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field, StrictBool
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import authenticated_user
from app.core.config import settings
from app.db.session import get_db
from app.models import (
    DocStatus,
    DocType,
    Document,
    DocumentAuditEvent,
    Extraction,
    ExtractionStatus,
    Land,
    LandAssessment,
    User,
)
from app.schemas.assessment import Action, Assessment, AssessmentOut
from app.schemas.document import (
    STATUS_LABELS_BN,
    DocumentStatusOut,
    LatestExtractionOut,
    count_needs_review,
)
from app.schemas.extracted import DeedData, ExtractedDocument
from app.schemas.extraction import ExtractionWarningOut
from app.schemas.identity import IdentityVerificationOut
from app.schemas.land_case import CaseRole, LandCase, LandIn, LandOut
from app.services.actions import next_actions
from app.services.deed_archive import compare_deeds, integrity_status
from app.services.land_case import load_land_case
from app.services.report import render_report_html, render_report_pdf
from app.services.risk import assess
from app.services.rules import run_rules
from app.services.rules.names import names_match, person_key
from app.services.storage import Storage, get_storage
from app.services.timeline import build_timeline

router = APIRouter(prefix="/lands", tags=["lands"])

Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(authenticated_user)]


def _owned_land(db: Session, land_id: uuid.UUID, user: User) -> Land:
    land = db.get(Land, land_id)
    if land is None or land.owner_id != user.id:
        raise HTTPException(404, "Land not found")
    return land


class ActionUpdateIn(BaseModel):
    done: StrictBool


def _doc_status_out(doc: Document, db: Session) -> DocumentStatusOut:
    latest = db.scalars(
        select(Extraction)
        .where(Extraction.document_id == doc.id)
        .order_by(Extraction.created_at.desc(), Extraction.id.desc())
    ).first()

    latest_extraction = None
    if latest is not None:
        latest_extraction = LatestExtractionOut(
            id=latest.id,
            status=latest.status,
            needs_review_count=count_needs_review(latest.field_flags),
            warnings_count=len(latest.warnings or []),
        )

    now = datetime.now(UTC)
    updated_at = doc.updated_at
    if updated_at is not None and updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=UTC)

    is_stale = False
    if doc.status == DocStatus.processing and updated_at is not None:
        is_stale = (now - updated_at).total_seconds() > settings.stale_after_minutes * 60

    poll_after_s = 2 if doc.status == DocStatus.processing else None

    return DocumentStatusOut(
        id=doc.id,
        original_filename=doc.original_filename,
        doc_type=doc.doc_type,
        detected_doc_type=doc.detected_doc_type,
        classify_confidence=doc.classify_confidence,
        status=doc.status,
        status_label_bn=STATUS_LABELS_BN.get(doc.status, ""),
        current_step=doc.current_step,
        step_label_bn=STATUS_LABELS_BN.get(doc.current_step, ""),
        label_warning=doc.label_warning,
        error_message=doc.error_message,
        attempts=doc.attempts,
        created_at=doc.created_at,
        started_at=doc.started_at,
        finished_at=doc.finished_at,
        updated_at=doc.updated_at,
        is_stale=is_stale,
        latest_extraction=latest_extraction,
        poll_after_s=poll_after_s,
    )


@router.post("", response_model=LandOut, status_code=201)
def create_land(body: LandIn, db: Db, user: CurrentUser):
    # ponytail: lands columns are NOT NULL; "" for an unknown district/upazila/khatian until a
    # migration makes them nullable
    land = Land(
        district=body.district or "",
        upazila=body.upazila or "",
        mouza=body.mouza,
        dag_no=body.dag_no,
        khatian_no=body.khatian_no or "",
        owner_id=user.id,
    )
    db.add(land)
    db.commit()
    return land


@router.get("/{land_id}", response_model=LandOut)
def get_land(land_id: uuid.UUID, db: Db, user: CurrentUser):
    return _owned_land(db, land_id, user)


@router.get("", response_model=list[LandOut])
def list_lands(db: Db, user: CurrentUser):
    return db.scalars(
        select(Land).where(Land.owner_id == user.id).order_by(Land.created_at.desc())
    ).all()


@router.get("/{land_id}/documents", response_model=list[DocumentStatusOut])
def list_land_documents(land_id: uuid.UUID, db: Db, user: CurrentUser):
    _owned_land(db, land_id, user)
    docs = db.scalars(
        select(Document).where(Document.land_id == land_id).order_by(Document.created_at.asc())
    ).all()
    return [_doc_status_out(doc, db) for doc in docs]


@router.get("/{land_id}/case", response_model=LandCase)
def get_land_case(land_id: uuid.UUID, db: Db, user: CurrentUser):
    """The land case as the rule engine will see it (debug view until the case page)."""
    _owned_land(db, land_id, user)
    return load_land_case(db, land_id)


@router.get("/{land_id}/timeline")
def land_timeline(land_id: uuid.UUID, db: Db, user: CurrentUser):
    """Document-backed ownership events with status from the latest assessment."""
    _owned_land(db, land_id, user)
    case = load_land_case(db, land_id)
    row = db.scalars(
        select(LandAssessment)
        .where(LandAssessment.land_id == land_id)
        .order_by(LandAssessment.created_at.desc(), LandAssessment.id.desc())
        .limit(1)
    ).first()
    if row is not None:
        assessment = Assessment(**row.result)
    else:
        run = run_rules(case)
        assessment = assess(case, run)
    return build_timeline(case, assessment)


class CaseViewExtractionOut(BaseModel):
    id: uuid.UUID
    extractor: str
    status: ExtractionStatus
    data: ExtractedDocument | dict[str, Any] | None = None
    warnings: list[ExtractionWarningOut] = Field(default_factory=list)
    field_flags: dict[str, Any] = Field(default_factory=dict)
    handwritten: bool = False
    created_at: datetime


class CaseViewDocOut(BaseModel):
    id: uuid.UUID
    original_filename: str
    doc_type: DocType | None = None
    label_bn: str
    role: CaseRole | None = None
    status: DocStatus
    file_url_endpoint: str
    latest_extraction: CaseViewExtractionOut | None = None


class LandCaseViewOut(BaseModel):
    land: LandOut
    documents: list[CaseViewDocOut]
    assessment_stale: bool
    latest_assessment: AssessmentOut | None = None
    identity_verifications: list[IdentityVerificationOut] = Field(default_factory=list)


class DeedArchiveFieldOut(BaseModel):
    key: str
    label_bn: str
    current: Any = None
    previous: Any = None
    current_field: str
    previous_field: str


class DeedArchiveItemOut(BaseModel):
    id: uuid.UUID
    original_filename: str
    file_url_endpoint: str
    created_at: datetime
    uploaded_by: str | None = None
    uploaded_at: datetime
    content_sha256: str | None = None
    data: DeedData | None = None
    previous_document_id: uuid.UUID | None = None
    comparison: list[DeedArchiveFieldOut] = Field(default_factory=list)
    source_type: str = "user_upload"
    integrity: str
    verification_status: str = "সরকারি উৎসে যাচাই হয়নি"
    extraction_id: uuid.UUID | None = None
    extraction_created_at: datetime | None = None
    extraction_created_by: str | None = None
    audit: list[dict[str, Any]] = Field(default_factory=list)


class DeedArchiveOut(BaseModel):
    items: list[DeedArchiveItemOut]
    official_source_verified: bool = False
    notice_bn: str = "সরকারি উৎসে আসলত্ব যাচাই করা হয়নি।"


@router.get("/{land_id}/deeds", response_model=DeedArchiveOut)
def list_land_deeds(
    land_id: uuid.UUID, db: Db, user: CurrentUser, storage: Annotated[Storage, Depends(get_storage)]
):
    """List the land's deed documents, source extractions and adjacent deed comparisons."""
    _owned_land(db, land_id, user)
    documents = db.scalars(
        select(Document)
        .where(Document.land_id == land_id)
        .order_by(Document.created_at.asc(), Document.id.asc())
    ).all()
    deeds = []
    for doc in documents:
        latest = db.scalars(
            select(Extraction)
            .where(Extraction.document_id == doc.id)
            .order_by(Extraction.created_at.desc(), Extraction.id.desc())
            .limit(1)
        ).first()
        raw = latest.data if latest and latest.data else None
        if not raw or raw.get("doc_type") != "deed":
            continue
        data = DeedData.model_validate(raw)
        uploader = str(doc.owner_id) if doc.owner_id else None
        deeds.append((doc, data, uploader))

    def deed_date(item):
        data = item[1]
        date_key = (
            data.registration_date.isoformat()
            if data.registration_date
            else (data.deed_year or "9999")
        )
        return date_key, item[0].created_at, str(item[0].id)

    deeds.sort(key=deed_date)
    items = []
    for index, (doc, data, uploader) in enumerate(deeds):
        previous = deeds[index - 1] if index else None
        items.append(
            DeedArchiveItemOut(
                id=doc.id,
                original_filename=doc.original_filename,
                file_url_endpoint=f"/documents/{doc.id}/file",
                created_at=doc.created_at,
                uploaded_by=uploader,
                uploaded_at=doc.created_at,
                content_sha256=doc.content_sha256,
                data=data,
                previous_document_id=previous[0].id if previous else None,
                comparison=compare_deeds(
                    data.model_dump(mode="json"), previous[1].model_dump(mode="json")
                )
                if previous
                else [],
                source_type=doc.source_type or "user_upload",
                integrity=integrity_status(doc, storage),
                extraction_id=latest.id,
                extraction_created_at=latest.created_at,
                extraction_created_by=latest.created_by,
                audit=[
                    {
                        "event": event.event,
                        "actor": event.actor,
                        "created_at": event.created_at,
                        "details": event.details,
                    }
                    for event in db.scalars(
                        select(DocumentAuditEvent)
                        .where(DocumentAuditEvent.document_id == doc.id)
                        .order_by(DocumentAuditEvent.created_at, DocumentAuditEvent.id)
                    ).all()
                ],
            )
        )
    return DeedArchiveOut(items=items)


@router.get("/{land_id}/deeds/compare")
def compare_land_deeds(
    land_id: uuid.UUID,
    db: Db,
    user: CurrentUser,
    a: Annotated[uuid.UUID, Query()],
    b: Annotated[uuid.UUID, Query()],
):
    _owned_land(db, land_id, user)
    selected = {}
    for document_id in (a, b):
        doc = db.scalar(
            select(Document).where(Document.id == document_id, Document.land_id == land_id)
        )
        if doc is None:
            raise HTTPException(404, "Deed not found")
        extraction = db.scalars(
            select(Extraction)
            .where(Extraction.document_id == doc.id)
            .order_by(Extraction.created_at.desc(), Extraction.id.desc())
        ).first()
        if extraction is None or not extraction.data or extraction.data.get("doc_type") != "deed":
            raise HTTPException(409, "Deed extraction not available")
        selected[document_id] = (doc, DeedData.model_validate(extraction.data))
    older_id, newer_id = sorted(
        (a, b),
        key=lambda document_id: (
            selected[document_id][1].registration_date.isoformat()
            if selected[document_id][1].registration_date
            else selected[document_id][1].deed_year or "9999",
            selected[document_id][0].created_at,
            str(document_id),
        ),
    )
    older, newer = selected[older_id][1], selected[newer_id][1]
    old_buyers = [p.name for p in older.buyers]
    new_sellers = [p.name for p in newer.sellers]
    chain_link = any(
        names_match(person_key(x), person_key(y))[0] for x in old_buyers for y in new_sellers
    )
    old_dags = {p.dag_no for p in older.schedule_plots}
    new_dags = {p.dag_no for p in newer.schedule_plots}
    old_area = older.transferred_area_shatangsho
    new_area = newer.transferred_area_shatangsho
    return {
        "a": str(a),
        "b": str(b),
        "older_document_id": str(older_id),
        "newer_document_id": str(newer_id),
        "fields": compare_deeds(newer.model_dump(mode="json"), older.model_dump(mode="json")),
        "links": {
            "buyer_to_seller": chain_link,
            "same_dag": bool(old_dags & new_dags),
            "area_within": old_area is not None and new_area is not None and new_area <= old_area,
        },
        "official_source_verified": False,
        "verification_status": "সরকারি উৎসে যাচাই হয়নি",
    }


def _out(row: LandAssessment) -> AssessmentOut:
    return AssessmentOut(id=row.id, land_id=row.land_id, created_at=row.created_at, **row.result)


@router.get("/{land_id}/case-view", response_model=LandCaseViewOut)
def get_land_case_view(land_id: uuid.UUID, db: Db, user: CurrentUser):
    """Case page overview: documents with latest extractions, file endpoint, role, and staleness."""
    land = _owned_land(db, land_id, user)

    docs = db.scalars(
        select(Document).where(Document.land_id == land_id).order_by(Document.created_at.asc())
    ).all()

    # Build land case for role & label_bn assignments
    case = load_land_case(db, land_id)
    case_doc_map = {d.source_id: d for d in case.documents}

    latest_assess = db.scalars(
        select(LandAssessment)
        .where(LandAssessment.land_id == land_id)
        .order_by(LandAssessment.created_at.desc())
        .limit(1)
    ).first()

    assess_out = _out(latest_assess) if latest_assess is not None else None
    assess_time = (
        latest_assess.created_at.replace(tzinfo=UTC)
        if latest_assess is not None and latest_assess.created_at.tzinfo is None
        else (latest_assess.created_at if latest_assess is not None else None)
    )

    doc_outs: list[CaseViewDocOut] = []
    assessment_stale = False

    for doc in docs:
        latest = db.scalars(
            select(Extraction)
            .where(Extraction.document_id == doc.id)
            .order_by(Extraction.created_at.desc(), Extraction.id.desc())
            .limit(1)
        ).first()

        cd = case_doc_map.get(str(doc.id))
        role = cd.role if cd is not None else None
        label_bn = (
            cd.label_bn
            if cd is not None
            else (
                STATUS_LABELS_BN.get(doc.status, "কাগজ")
                + (f" ({doc.original_filename})" if doc.original_filename else "")
            )
        )

        ext_out = None
        if latest is not None:
            ext_out = CaseViewExtractionOut(
                id=latest.id,
                extractor=latest.extractor,
                status=latest.status,
                data=latest.data,
                warnings=[
                    ExtractionWarningOut(**w) if isinstance(w, dict) else w
                    for w in (latest.warnings or [])
                ],
                field_flags=latest.field_flags or {},
                handwritten=latest.handwritten,
                created_at=latest.created_at,
            )
            ext_time = (
                latest.created_at.replace(tzinfo=UTC)
                if latest.created_at.tzinfo is None
                else latest.created_at
            )
            if assess_time is None or ext_time > assess_time:
                assessment_stale = True

        doc_outs.append(
            CaseViewDocOut(
                id=doc.id,
                original_filename=doc.original_filename,
                doc_type=doc.doc_type,
                label_bn=label_bn,
                role=role,
                status=doc.status,
                file_url_endpoint=f"/documents/{doc.id}/file",
                latest_extraction=ext_out,
            )
        )

    return LandCaseViewOut(
        land=LandOut.model_validate(land),
        documents=doc_outs,
        assessment_stale=assessment_stale,
        latest_assessment=assess_out,
        identity_verifications=case.identity_records,
    )


@router.post("/{land_id}/assess", response_model=AssessmentOut, status_code=201)
def assess_land(land_id: uuid.UUID, db: Db, user: CurrentUser):
    """Run the rules on the land case, store the assessment and return it."""
    _owned_land(db, land_id, user)
    case = load_land_case(db, land_id)
    run = run_rules(case)
    assessment = assess(case, run)
    assessment.actions = next_actions(case, run, assessment)
    row = LandAssessment(
        land_id=land_id,
        engine_version=assessment.engine_version,
        risk_level=assessment.risk_level,
        result=assessment.model_dump(mode="json"),
    )
    db.add(row)
    db.commit()
    return _out(row)


@router.get("/{land_id}/assessments/latest", response_model=AssessmentOut)
def latest_assessment(land_id: uuid.UUID, db: Db, user: CurrentUser):
    _owned_land(db, land_id, user)
    row = db.scalars(
        select(LandAssessment)
        .where(LandAssessment.land_id == land_id)
        .order_by(LandAssessment.created_at.desc())
        .limit(1)
    ).first()
    if row is None:
        raise HTTPException(404, "No assessment for this land")
    return _out(row)


@router.get("/{land_id}/assessments", response_model=list[AssessmentOut])
def list_assessments(land_id: uuid.UUID, db: Db, user: CurrentUser):
    _owned_land(db, land_id, user)
    rows = db.scalars(
        select(LandAssessment)
        .where(LandAssessment.land_id == land_id)
        .order_by(LandAssessment.created_at.desc(), LandAssessment.id.desc())
    ).all()
    return [_out(row) for row in rows]


@router.get("/{land_id}/assessments/{assessment_id}/diff")
def assessment_diff(land_id: uuid.UUID, assessment_id: uuid.UUID, db: Db, user: CurrentUser):
    _owned_land(db, land_id, user)
    rows = db.scalars(
        select(LandAssessment)
        .where(LandAssessment.land_id == land_id)
        .order_by(LandAssessment.created_at.desc(), LandAssessment.id.desc())
        .limit(100)
    ).all()
    current = next((row for row in rows if row.id == assessment_id), None)
    if current is None:
        raise HTTPException(404, "Assessment not found")
    previous = next((row for row in rows if row.id != assessment_id), None)
    if previous is None:
        return {
            "previous": None,
            "risk_level": current.risk_level,
            "added_findings": [],
            "removed_findings": [],
        }
    now_codes = {f.get("code") for f in current.result.get("findings", []) if f.get("code")}
    old_codes = {f.get("code") for f in previous.result.get("findings", []) if f.get("code")}
    return {
        "previous": {"id": str(previous.id), "risk_level": previous.risk_level},
        "risk_level": current.risk_level,
        "added_findings": sorted(now_codes - old_codes),
        "removed_findings": sorted(old_codes - now_codes),
    }


@router.put("/{land_id}/actions/{action_id}", response_model=Action)
def update_action(
    land_id: uuid.UUID, action_id: str, body: ActionUpdateIn, db: Db, user: CurrentUser
):
    _owned_land(db, land_id, user)
    row = db.scalars(
        select(LandAssessment)
        .where(LandAssessment.land_id == land_id)
        .order_by(LandAssessment.created_at.desc(), LandAssessment.id.desc())
        .limit(1)
    ).first()
    if row is None:
        raise HTTPException(404, "Action not found")
    result = dict(row.result)
    actions = [dict(action) for action in result.get("actions", [])]
    action = next((item for item in actions if item.get("id") == action_id), None)
    if action is None:
        raise HTTPException(404, "Action not found")
    action["done"] = body.done
    result["actions"] = actions
    row.result = result
    db.commit()
    return Action.model_validate(action)


def _report_filename(land: Land) -> str:
    """ASCII file name: mouza and dag if they are ASCII, else the land id."""
    parts = [land.mouza, land.dag_no]
    if all(p and p.isascii() for p in parts):
        slug = "-".join(re.sub(r"[^A-Za-z0-9]+", "_", p).strip("_") for p in parts)
    else:
        slug = str(land.id)
    return f"jomiguard-report-{slug}.pdf"


@router.get("/{land_id}/assessments/{assessment_id}/report.pdf")
def assessment_report(land_id: uuid.UUID, assessment_id: uuid.UUID, db: Db, user: CurrentUser):
    """The assessment as a Bangla PDF (documents as they are now in the land case)."""
    land = _owned_land(db, land_id, user)
    row = db.get(LandAssessment, assessment_id)
    if row is None or row.land_id != land_id:
        raise HTTPException(404, "Assessment not found")
    case = load_land_case(db, land_id)
    html = render_report_html(case, Assessment(**row.result), datetime.now(UTC))
    return Response(
        render_report_pdf(html),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{_report_filename(land)}"'},
    )
