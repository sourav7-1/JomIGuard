"""Idempotent synthetic guardian demo data; never invokes an extractor."""

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    DocStatus,
    DocType,
    Document,
    Extraction,
    ExtractionStatus,
    GuardedLand,
    GuardianAlert,
    GuardianSnapshot,
    IdentityVerification,
    User,
)
from app.models.document import DocStep
from app.schemas.extracted import KhatianData
from app.services.normalize import normalize_document
from app.services.storage import get_storage

ROOT = Path(__file__).resolve().parents[3] / "data/synthetic/cases/case_00001"
SPECS = (
    ("\u09e7\u09e6\u09e8", "\u09ac\u09b0\u09bf\u09b6\u09be\u09b2 \u09b8\u09a6\u09b0"),
    ("\u09e7\u09e6\u09ee", "\u0989\u099c\u09bf\u09b0\u09aa\u09c1\u09b0"),
    ("\u09e8\u09e8\u09e7", "\u0997\u09cc\u09b0\u09a8\u09a6\u09c0"),
    ("\u09e9\u09e6\u09eb", "\u09ac\u09be\u0995\u09c7\u09b0\u0997\u099e\u09cd\u099c"),
    ("\u09ea\u09e7\u09e6", "\u09ac\u09b0\u09bf\u09b6\u09be\u09b2 \u09b8\u09a6\u09b0"),
)
NASIR = "\u09a8\u09be\u09b8\u09bf\u09b0 \u0989\u09a6\u09cd\u09a6\u09bf\u09a8"


def _uid(value: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"jomiguard-{value}")


def _unmangle(value: str) -> str:
    try:
        return value.encode("cp1252").decode("utf-8")
    except UnicodeError:
        return value


def _store_seed_file(storage, key: str, data: bytes, content_type: str = "image/png") -> str:
    fingerprint = hashlib.sha256(data).hexdigest()
    storage.upload(key, data, content_type)
    if hashlib.sha256(storage.download(key)).hexdigest() != fingerprint:
        raise RuntimeError(f"Guardian seed fingerprint verification failed: {key}")
    return fingerprint


def seed_guardian(db: Session):
    user = db.scalar(select(User).where(User.username == settings.admin_username))
    if user is None:
        return
    storage = get_storage()
    storage.ensure_bucket()
    png = (ROOT / "khatian.png").read_bytes()
    raw = json.loads((ROOT / "khatian.json").read_text(encoding="utf-8"))
    raw["owners"] = [
        {"name": NASIR, "name_normalized": NASIR, "share_text": "\u09e7.\u09e6\u09e6\u09e6"}
    ]

    # Remove only the previous demo's mojibaked labels; preserve user-created lands.
    dag_set = {dag for dag, _ in SPECS}
    bad_prefix = "\u09a6\u09be\u0997".encode("utf-8").decode("cp1252")
    for row in db.scalars(select(GuardedLand).where(GuardedLand.user_id == user.id)).all():
        if _unmangle(row.dag_no) in dag_set and row.label_bn.startswith(bad_prefix):
            db.delete(row)

    for index, (dag, upazila) in enumerate(SPECS):
        gid = _uid(f"guardian-land-{dag}")
        baseline_id = _uid(f"guardian-base-doc-{dag}")
        data_in = json.loads(json.dumps(raw))
        data_in["location"].update(
            district="\u09ac\u09b0\u09bf\u09b6\u09be\u09b2",
            upazila=upazila,
            mouza=f"\u09a1\u09c7\u09ae\u09cb \u09ae\u09cc\u099c\u09be {dag}",
        )
        data_in["khatian_no"] = f"G-{index + 1}"
        data_in["plots"] = [
            {
                "dag_no": dag,
                "area_text": "\u09e7.\u09e6\u09e6\u09e6",
                "area_shatangsho": "100",
                "plot_total_area_text": "\u09e7.\u09e6\u09e6\u09e6",
                "plot_total_area_shatangsho": "100",
                "khatian_share_text": "\u09e7.\u09e6\u09e6\u09e6",
                "khatian_share_fraction": "1.000",
            }
        ]
        data_in["total_area_text"], data_in["total_area_shatangsho"] = (
            "\u09e7.\u09e6\u09e6\u09e6",
            "100",
        )
        data = normalize_document(KhatianData.model_validate(data_in)).doc.model_dump(mode="json")
        key = f"guardian/demo/{dag}/baseline.png"
        fingerprint = _store_seed_file(storage, key, png)
        doc = db.get(Document, baseline_id)
        if doc is None:
            doc = Document(
                id=baseline_id,
                owner_id=user.id,
                doc_type=DocType.khatian,
                file_key=key,
                original_filename=f"guardian-base-{dag}.png",
            )
            db.add(doc)
        doc.file_key = key
        doc.original_filename = f"guardian-base-{dag}.png"
        doc.content_sha256 = fingerprint
        doc.doc_type = DocType.khatian
        doc.owner_id, doc.status, doc.current_step, doc.detected_doc_type = (
            user.id,
            DocStatus.done,
            DocStep.finished,
            DocType.khatian,
        )
        extraction_id = _uid(f"guardian-base-extraction-{dag}")
        ex = db.get(Extraction, extraction_id)
        if ex is None:
            ex = Extraction(
                id=extraction_id,
                document_id=doc.id,
                extractor="seed",
                created_by="seed",
                status=ExtractionStatus.ok,
                cost_usd=0,
                latency_s=0,
            )
            db.add(ex)
        ex.data, ex.extractor, ex.status, ex.field_flags, ex.warnings = (
            data,
            "seed",
            ExtractionStatus.ok,
            {},
            [],
        )

        guarded = db.get(GuardedLand, gid)
        if guarded is None:
            guarded = GuardedLand(
                id=gid,
                user_id=user.id,
                label_bn=f"\u09a6\u09be\u0997 {dag} \u00b7 {upazila}",
                district="\u09ac\u09b0\u09bf\u09b6\u09be\u09b2",
                upazila=upazila,
                mouza=f"\u09a1\u09c7\u09ae\u09cb \u09ae\u09cc\u099c\u09be {dag}",
                dag_no=dag,
                khatian_no=f"G-{index + 1}",
            )
            db.add(guarded)
        else:
            guarded.user_id = user.id
        db.execute(delete(GuardianAlert).where(GuardianAlert.guarded_land_id == gid))
        guarded.baseline_snapshot_id = None
        db.flush()
        db.execute(delete(GuardianSnapshot).where(GuardianSnapshot.guarded_land_id == gid))
        db.flush()
        snap_id = _uid(f"guardian-base-snapshot-{dag}")
        db.add(
            GuardianSnapshot(
                id=snap_id,
                guarded_land_id=gid,
                document_id=doc.id,
                extraction_id=ex.id,
                data=data,
            )
        )
        guarded.baseline_snapshot_id = snap_id

        if dag in ("\u09e9\u09e6\u09eb", "\u09e8\u09e8\u09e7"):
            new_data = json.loads(json.dumps(data))
            if dag == "\u09e9\u09e6\u09eb":
                new_data["owners"] = [
                    {
                        "name": "\u09ae\u09cb\u0983 \u099c\u09b2\u09bf\u09b2",
                        "name_normalized": "\u09ae\u09cb\u0983 \u099c\u09b2\u09bf\u09b2",
                        "share_text": "\u09e7.\u09e6\u09e6\u09e6",
                    }
                ]
                new_data["mutation_case_ref"] = "\u09e7\u09e8\u09ea\u09e9/\u09e8\u09ec"
            else:
                new_data["annual_revenue_text"] = "\u09ef\u09ef \u099f\u09be\u0995\u09be"
            new_id = _uid(f"guardian-new-doc-{dag}")
            new_key = f"guardian/demo/{dag}/new.png"
            new_fingerprint = _store_seed_file(storage, new_key, png)
            new_doc = db.get(Document, new_id)
            if new_doc is None:
                new_doc = Document(
                    id=new_id,
                    owner_id=user.id,
                    doc_type=DocType.khatian,
                    file_key=new_key,
                    original_filename=f"guardian-demo-{dag}.png",
                    status=DocStatus.done,
                    current_step=DocStep.finished,
                    detected_doc_type=DocType.khatian,
                )
                db.add(new_doc)
            new_doc.file_key = new_key
            new_doc.original_filename = f"guardian-demo-{dag}.png"
            new_doc.content_sha256 = new_fingerprint
            new_doc.owner_id = user.id
            new_doc.doc_type = DocType.khatian
            new_doc.status = DocStatus.done
            new_doc.current_step = DocStep.finished
            new_doc.detected_doc_type = DocType.khatian
            new_ex_id = _uid(f"guardian-new-extraction-{dag}")
            new_ex = db.get(Extraction, new_ex_id)
            if new_ex is None:
                new_ex = Extraction(
                    id=new_ex_id,
                    document_id=new_doc.id,
                    extractor="seed",
                    created_by="seed",
                    status=ExtractionStatus.ok,
                    cost_usd=0,
                    latency_s=0,
                )
                db.add(new_ex)
            new_ex.data, new_ex.extractor, new_ex.status = new_data, "seed", ExtractionStatus.ok
            new_ex.field_flags, new_ex.warnings = {}, []

    # Rebuild missing content for older guardian seed rows.
    legacy_docs = db.scalars(
        select(Document).where(
            Document.owner_id == user.id,
            Document.original_filename.like("guardian-demo-%.json"),
        )
    ).all()
    for legacy_doc in legacy_docs:
        extraction = db.scalar(
            select(Extraction)
            .where(Extraction.document_id == legacy_doc.id)
            .order_by(Extraction.created_at.desc())
        )
        if extraction and extraction.data:
            payload = json.dumps(
                extraction.data, ensure_ascii=False, separators=(",", ":")
            ).encode()
            legacy_doc.content_sha256 = _store_seed_file(
                storage, legacy_doc.file_key, payload, "application/json"
            )

    if (
        db.scalar(
            select(IdentityVerification.id).where(
                IdentityVerification.user_id == user.id,
                IdentityVerification.provider_ref == "guardian-demo-buyer",
            )
        )
        is None
    ):
        db.add(
            IdentityVerification(
                user_id=user.id,
                land_id=None,
                party="buyer",
                status="verified",
                name_bn_as_per_nid=NASIR,
                father_name_as_per_nid=None,
                provider="mock",
                provider_ref="guardian-demo-buyer",
                consent_at=datetime.now(UTC),
                consent_version="guardian-demo",
                verified_at=datetime.now(UTC),
            )
        )
    db.commit()
