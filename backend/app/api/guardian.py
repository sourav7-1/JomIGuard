import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import authenticated_user
from app.db.session import get_db
from app.models import (
    Document,
    Extraction,
    GuardedLand,
    GuardianAlert,
    GuardianSnapshot,
    IdentityVerification,
    User,
)
from app.services.deed_archive import integrity_status
from app.services.guardian import diff_khatians
from app.services.report import render_report_pdf
from app.services.storage import get_storage

router = APIRouter(prefix="/guardian", tags=["guardian"])
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(authenticated_user)]


class AddLandIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: uuid.UUID


def _document(db, document_id, user):
    doc = db.scalar(
        select(Document).where(Document.id == document_id, Document.owner_id == user.id)
    )
    if doc is None or str(doc.doc_type) not in ("khatian", "DocType.khatian"):
        raise HTTPException(404, "খতিয়ানের নথি পাওয়া যায়নি")
    extraction = db.scalar(
        select(Extraction)
        .where(Extraction.document_id == doc.id, Extraction.status != "failed")
        .order_by(Extraction.created_at.desc())
    )
    if extraction is None or not extraction.data:
        raise HTTPException(422, "খতিয়ানের extraction প্রস্তুত নয়")
    return doc, extraction


def _new_snapshot(db, guarded, doc, extraction):
    row = GuardianSnapshot(
        guarded_land_id=guarded.id,
        document_id=doc.id,
        extraction_id=extraction.id,
        data=extraction.data,
    )
    db.add(row)
    db.flush()
    return row


@router.post("/lands", status_code=201)
def add_guarded_land(body: AddLandIn, db: Db, user: CurrentUser):
    doc, extraction = _document(db, body.document_id, user)
    data = extraction.data
    dag = data["plots"][0]["dag_no"] if data.get("plots") else ""
    guarded = GuardedLand(
        user_id=user.id,
        label_bn=f"দাগ {dag} · {data['location']['mouza']}",
        district=data["location"]["district"],
        upazila=data["location"]["upazila"],
        mouza=data["location"]["mouza"],
        dag_no=data["plots"][0]["dag_no"] if data.get("plots") else "",
        khatian_no=data["khatian_no"],
    )
    db.add(guarded)
    db.flush()
    snapshot = _new_snapshot(db, guarded, doc, extraction)
    guarded.baseline_snapshot_id = snapshot.id
    db.commit()
    return _land_out(db, guarded)


def _land_out(db, land):
    unread = db.scalars(
        select(GuardianAlert).where(
            GuardianAlert.guarded_land_id == land.id, GuardianAlert.read_at.is_(None)
        )
    ).all()
    latest = db.scalar(
        select(GuardianSnapshot)
        .where(GuardianSnapshot.guarded_land_id == land.id)
        .order_by(GuardianSnapshot.taken_at.desc())
    )
    snapshots = db.scalars(
        select(GuardianSnapshot).where(GuardianSnapshot.guarded_land_id == land.id)
    ).all()
    document_ids = {snapshot.document_id for snapshot in snapshots}
    demo_docs = db.scalars(
        select(Document).where(
            Document.owner_id == land.user_id,
            Document.original_filename == f"guardian-demo-{land.dag_no}.png",
        )
    ).all()
    document_ids.update(doc.id for doc in demo_docs)
    docs = db.scalars(
        select(Document)
        .where(Document.id.in_(document_ids), Document.owner_id == land.user_id)
        .order_by(Document.created_at)
    ).all()
    return {
        "id": str(land.id),
        "label_bn": land.label_bn,
        "district": land.district,
        "upazila": land.upazila,
        "mouza": land.mouza,
        "dag_no": land.dag_no,
        "khatian_no": land.khatian_no,
        "last_checked_at": land.last_checked_at,
        "status": "bad" if any(a.severity == "bad" for a in unread) else "warn" if unread else "ok",
        "unread_alerts": len(unread),
        "demo_document_id": str(demo_docs[0].id) if demo_docs else None,
        "documents": [
            {
                "id": str(doc.id),
                "original_filename": doc.original_filename,
                "integrity": integrity_status(doc, get_storage()),
            }
            for doc in docs
        ],
        "current_snapshot": latest.data if latest else None,
    }


@router.get("/lands")
def list_guarded_lands(db: Db, user: CurrentUser):
    rows = db.scalars(
        select(GuardedLand).where(GuardedLand.user_id == user.id).order_by(GuardedLand.created_at)
    ).all()
    return [_land_out(db, row) for row in rows]


def _check(db, land, document_id, user):
    doc, extraction = _document(db, document_id, user)
    old = db.get(GuardianSnapshot, land.baseline_snapshot_id)
    if old is None:
        raise HTTPException(409, "Baseline snapshot missing")
    identity = db.scalar(
        select(IdentityVerification)
        .where(
            IdentityVerification.user_id == user.id,
            IdentityVerification.party == "buyer",
            IdentityVerification.status == "verified",
        )
        .order_by(IdentityVerification.created_at.desc())
    )
    name = identity.name_bn_as_per_nid if identity else None
    result = diff_khatians(
        old.data,
        extraction.data,
        name,
        extraction.field_flags.keys() if extraction.field_flags else (),
    )
    new = _new_snapshot(db, land, doc, extraction)
    alert = None
    if result["changes"]:
        message = next(
            (c["message_bn"] for c in result["changes"] if c["severity"] == result["severity"]),
            "খতিয়ানে পরিবর্তন ধরা পড়েছে",
        )
        alert = GuardianAlert(
            guarded_land_id=land.id,
            from_snapshot_id=old.id,
            to_snapshot_id=new.id,
            severity=result["severity"],
            changes=result["changes"],
            message_bn=message,
        )
        db.add(alert)
    land.last_checked_at = datetime.now(UTC)
    land.baseline_snapshot_id = new.id
    db.commit()
    return {
        "alert_id": str(alert.id) if alert else None,
        "severity": result["severity"],
        "changes": result["changes"],
    }


@router.post("/lands/{land_id}/check")
def check_land(land_id: uuid.UUID, body: AddLandIn, db: Db, user: CurrentUser):
    land = db.scalar(
        select(GuardedLand).where(GuardedLand.id == land_id, GuardedLand.user_id == user.id)
    )
    if land is None:
        raise HTTPException(404, "Guarded land not found")
    return _check(db, land, body.document_id, user)


@router.post("/demo-check")
def demo_check(db: Db, user: CurrentUser):
    lands = db.scalars(select(GuardedLand).where(GuardedLand.user_id == user.id)).all()
    out = []
    for land in lands:
        doc = db.scalar(
            select(Document).where(
                Document.owner_id == user.id,
                Document.original_filename == f"guardian-demo-{land.dag_no}.png",
            )
        )
        if doc:
            out.append({"land_id": str(land.id), **_check(db, land, doc.id, user)})
    return out


@router.get("/lands/{land_id}/alerts")
def list_alerts(land_id: uuid.UUID, db: Db, user: CurrentUser):
    land = db.scalar(
        select(GuardedLand.id).where(GuardedLand.id == land_id, GuardedLand.user_id == user.id)
    )
    if land is None:
        raise HTTPException(404, "Guarded land not found")
    rows = db.scalars(
        select(GuardianAlert)
        .where(GuardianAlert.guarded_land_id == land_id)
        .order_by(GuardianAlert.created_at.desc())
    ).all()
    result = []
    for alert in rows:
        before, after = (
            db.get(GuardianSnapshot, alert.from_snapshot_id),
            db.get(GuardianSnapshot, alert.to_snapshot_id),
        )
        result.append(
            {
                "id": str(alert.id),
                "severity": alert.severity,
                "message_bn": alert.message_bn,
                "changes": alert.changes,
                "created_at": alert.created_at,
                "read_at": alert.read_at,
                "old": before.data,
                "new": after.data,
            }
        )
    return result


@router.post("/alerts/{alert_id}/read")
def read_alert(alert_id: uuid.UUID, db: Db, user: CurrentUser):
    alert = db.scalar(
        select(GuardianAlert)
        .join(GuardedLand)
        .where(GuardianAlert.id == alert_id, GuardedLand.user_id == user.id)
    )
    if alert is None:
        raise HTTPException(404, "Alert not found")
    alert.read_at = datetime.now(UTC)
    db.commit()
    return {"read": True}


@router.post("/alerts/{alert_id}/case-file")
def alert_case_file(alert_id: uuid.UUID, db: Db, user: CurrentUser):
    alert = db.scalar(
        select(GuardianAlert)
        .join(GuardedLand)
        .where(GuardianAlert.id == alert_id, GuardedLand.user_id == user.id)
    )
    if alert is None:
        raise HTTPException(404, "Alert not found")
    old, new = (
        db.get(GuardianSnapshot, alert.from_snapshot_id).data,
        db.get(GuardianSnapshot, alert.to_snapshot_id).data,
    )
    from html import escape

    changes = "".join(
        f"<li><strong>{escape(str(c['field']))}</strong>: "
        f"{escape(str(c.get('old') or '—'))} → "
        f"<mark>{escape(str(c.get('new') or '—'))}</mark> — "
        f"{escape(str(c['message_bn']))}</li>"
        for c in alert.changes
    )
    html = f"""<!doctype html><html lang="bn"><meta charset="utf-8">
<style>
body {{ font-family: 'Noto Sans Bengali', sans-serif; margin: 36px; color: #183b32; }}
h1 {{ color: #164e3d; }}
section {{ border: 1px solid #ccd9d2; padding: 16px; margin: 12px 0; }}
mark {{ background: #ffdf79; }} li {{ margin: 12px; }}
</style>
<h1>খতিয়ান পরিবর্তনের case file</h1><p>{escape(alert.message_bn)}</p>
<section><h2>আগের খতিয়ান</h2><pre>{escape(str(old))}</pre></section>
<section><h2>নতুন খতিয়ান</h2><pre>{escape(str(new))}</pre></section>
<h2>পরিবর্তন</h2><ul>{changes}</ul><p>তথ্য যাচাই করা দরকার।</p></html>"""
    return Response(
        render_report_pdf(html),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="guardian-case-{alert_id}.pdf"'},
    )


@router.get("/objection-guide")
def objection_guide():
    from pathlib import Path

    source = Path(__file__).resolve().parents[3] / "docs/legal-notes.md"
    return {"text": source.read_text(encoding="utf-8"), "notice_bn": "যাচাই করা দরকার"}
