import re
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import (
    DocStatus,
    DocType,
    Document,
    Extraction,
    ExtractionStatus,
    Land,
    LandAssessment,
)
from app.schemas.assessment import Assessment, AssessmentOut
from app.schemas.document import (
    STATUS_LABELS_BN,
    DocumentStatusOut,
    LatestExtractionOut,
    count_needs_review,
)
from app.schemas.extracted import ExtractedDocument
from app.schemas.extraction import ExtractionWarningOut
from app.schemas.land_case import CaseRole, LandCase, LandIn, LandOut
from app.services.actions import next_actions
from app.services.land_case import load_land_case
from app.services.report import render_report_html, render_report_pdf
from app.services.risk import assess
from app.services.rules import run_rules

router = APIRouter(prefix="/lands", tags=["lands"])

Db = Annotated[Session, Depends(get_db)]


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
def create_land(body: LandIn, db: Db):
    # ponytail: lands columns are NOT NULL; "" for an unknown district/upazila/khatian until a
    # migration makes them nullable
    land = Land(
        district=body.district or "",
        upazila=body.upazila or "",
        mouza=body.mouza,
        dag_no=body.dag_no,
        khatian_no=body.khatian_no or "",
    )
    db.add(land)
    db.commit()
    return land


@router.get("/{land_id}", response_model=LandOut)
def get_land(land_id: uuid.UUID, db: Db):
    land = db.get(Land, land_id)
    if land is None:
        raise HTTPException(404, "Land not found")
    return land


@router.get("/{land_id}/documents", response_model=list[DocumentStatusOut])
def list_land_documents(land_id: uuid.UUID, db: Db):
    if db.get(Land, land_id) is None:
        raise HTTPException(404, "Land not found")
    docs = db.scalars(
        select(Document).where(Document.land_id == land_id).order_by(Document.created_at.asc())
    ).all()
    return [_doc_status_out(doc, db) for doc in docs]


@router.get("/{land_id}/case", response_model=LandCase)
def get_land_case(land_id: uuid.UUID, db: Db):
    """The land case as the rule engine will see it (debug view until the case page)."""
    if db.get(Land, land_id) is None:
        raise HTTPException(404, "Land not found")
    return load_land_case(db, land_id)


class CaseViewExtractionOut(BaseModel):
    id: uuid.UUID
    extractor: str
    status: ExtractionStatus
    data: ExtractedDocument | dict[str, Any] | None = None
    warnings: list[ExtractionWarningOut] = Field(default_factory=list)
    field_flags: dict[str, Any] = Field(default_factory=dict)
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


def _out(row: LandAssessment) -> AssessmentOut:
    return AssessmentOut(id=row.id, land_id=row.land_id, created_at=row.created_at, **row.result)


@router.get("/{land_id}/case-view", response_model=LandCaseViewOut)
def get_land_case_view(land_id: uuid.UUID, db: Db):
    """Case page overview: documents with latest extractions, file endpoint, role, and staleness."""
    land = db.get(Land, land_id)
    if land is None:
        raise HTTPException(404, "Land not found")

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
    )


@router.post("/{land_id}/assess", response_model=AssessmentOut, status_code=201)
def assess_land(land_id: uuid.UUID, db: Db):
    """Run the rules on the land case, store the assessment and return it."""
    if db.get(Land, land_id) is None:
        raise HTTPException(404, "Land not found")
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
def latest_assessment(land_id: uuid.UUID, db: Db):
    row = db.scalars(
        select(LandAssessment)
        .where(LandAssessment.land_id == land_id)
        .order_by(LandAssessment.created_at.desc())
        .limit(1)
    ).first()
    if row is None:
        raise HTTPException(404, "No assessment for this land")
    return _out(row)


def _report_filename(land: Land) -> str:
    """ASCII file name: mouza and dag if they are ASCII, else the land id."""
    parts = [land.mouza, land.dag_no]
    if all(p and p.isascii() for p in parts):
        slug = "-".join(re.sub(r"[^A-Za-z0-9]+", "_", p).strip("_") for p in parts)
    else:
        slug = str(land.id)
    return f"jomiguard-report-{slug}.pdf"


@router.get("/{land_id}/assessments/{assessment_id}/report.pdf")
def assessment_report(land_id: uuid.UUID, assessment_id: uuid.UUID, db: Db):
    """The assessment as a Bangla PDF (documents as they are now in the land case)."""
    land = db.get(Land, land_id)
    row = db.get(LandAssessment, assessment_id)
    if land is None or row is None or row.land_id != land_id:
        raise HTTPException(404, "Assessment not found")
    case = load_land_case(db, land_id)
    html = render_report_html(case, Assessment(**row.result), datetime.now(UTC))
    return Response(
        render_report_pdf(html),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{_report_filename(land)}"'},
    )
