"""Seed the three synthetic demo cases without calling an extraction provider."""

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import (
    DocStatus,
    DocType,
    Document,
    DocumentAuditEvent,
    Extraction,
    ExtractionStatus,
    IdentityVerification,
    Land,
    LandAssessment,
    SellerLink,
    User,
)
from app.models.document import DocStep
from app.schemas.extracted import DeedData, HeirCertData, KhatianData, MutationData
from app.services.actions import next_actions
from app.services.extraction.prompts import PROMPT_VERSION
from app.services.normalize import normalize_document
from app.services.risk import assess
from app.services.rules import run_rules
from app.services.storage import get_storage

ROOT = Path(__file__).resolve().parents[3] / "data/synthetic/cases"
CASE_IDS = ("00001", "00026", "00029")
MODELS = {
    "khatian": KhatianData,
    "deed": DeedData,
    "mutation": MutationData,
    "dcr": MutationData,
    "heir_cert": HeirCertData,
}


def _cache_result(image: bytes, doc_type: str, cache_dir: Path):
    import hashlib

    for path in cache_dir.glob("*.json"):
        cached = json.loads(path.read_text(encoding="utf-8"))
        meta = cached.get("meta", {})
        model = meta.get("model")
        if meta.get("provider") != "gemini" or not model:
            continue
        digest = hashlib.sha256(image)
        for part in ("gemini", model, PROMPT_VERSION, doc_type, "gray"):
            digest.update(b"\0" + part.encode())
        if (
            path.stem == digest.hexdigest()
            and cached.get("error") is None
            and cached.get("tool_input")
        ):
            return (
                MODELS[doc_type].model_validate({**cached["tool_input"], "doc_type": doc_type}),
                model,
            )
    return None, None


def seed_case(
    case_id: str, folder: Path, db: Session, storage, cache_dir: Path
) -> tuple[uuid.UUID, str, list[str]]:
    admin = db.scalar(select(User).where(User.username == settings.admin_username))
    if admin is None:
        raise RuntimeError("Configured admin user is missing; start the backend first")
    meta = json.loads((folder / "case.json").read_text(encoding="utf-8"))
    land_id = uuid.uuid5(uuid.NAMESPACE_URL, f"jomiguard-demo-{case_id}")
    land = db.get(Land, land_id)
    if land is None:
        land = Land(
            id=land_id,
            owner_id=admin.id,
            district="",
            upazila="",
            mouza="",
            dag_no="",
            khatian_no="",
        )
        db.add(land)
    land.owner_id = admin.id
    db.execute(
        delete(IdentityVerification).where(
            IdentityVerification.land_id == land_id, IdentityVerification.party == "seller"
        )
    )
    db.execute(delete(SellerLink).where(SellerLink.land_id == land_id))

    seeded = []
    khatian = None
    registered_deed = None
    for doc_type in meta["documents"]:
        image_path = folder / f"{doc_type}.png"
        raw_path = folder / f"{doc_type}.json"
        image = image_path.read_bytes()
        cached, model = _cache_result(
            image, "dcr" if doc_type == "mutation" else doc_type, cache_dir
        )
        extracted = cached
        if extracted is None:
            seeded.append(doc_type)
            extracted = MODELS["dcr" if doc_type == "mutation" else doc_type].model_validate_json(
                raw_path.read_bytes()
            )
        normalized = normalize_document(extracted)
        data = normalized.doc
        kind = "dcr" if doc_type == "mutation" else doc_type
        doc_id = uuid.uuid5(land_id, kind)
        key = f"demo/{case_id}/{doc_type}.png"
        storage.upload(key, image, "image/png")
        doc = db.get(Document, doc_id)
        if doc is None:
            doc = Document(
                id=doc_id,
                land_id=land_id,
                doc_type=DocType(kind),
                file_key=key,
                original_filename=image_path.name,
            )
            db.add(doc)
            db.add(
                DocumentAuditEvent(
                    document_id=doc_id,
                    event="uploaded",
                    actor="seed",
                    details={"source_type": "user_upload"},
                )
            )
        doc.land_id, doc.doc_type, doc.file_key = land_id, DocType(kind), key
        doc.content_sha256 = hashlib.sha256(image).hexdigest()
        doc.owner_id = admin.id
        doc.detected_doc_type, doc.classify_confidence = DocType(kind), 1.0
        doc.status, doc.current_step = DocStatus.done, DocStep.finished
        doc.error_message, doc.label_warning, doc.finished_at = None, None, datetime.now(UTC)
        ex = db.scalars(
            select(Extraction)
            .where(Extraction.document_id == doc_id)
            .order_by(Extraction.created_at.desc())
            .limit(1)
        ).first()
        if ex is None:
            ex = Extraction(document_id=doc_id)
            db.add(ex)
        ex.extractor = "gemini" if cached is not None else "seed"
        ex.created_by = "ai" if cached is not None else "seed"
        ex.model = model
        ex.prompt_version = PROMPT_VERSION if cached is not None else None
        ex.status = ExtractionStatus.needs_review if normalized.warnings else ExtractionStatus.ok
        ex.data = data.model_dump(mode="json")
        ex.warnings = [w.__dict__ for w in normalized.warnings]
        flags: dict[str, list[str]] = {}
        for warning in normalized.warnings:
            flags.setdefault(warning.field_path, []).append(warning.code)
        ex.field_flags = flags
        ex.cost_usd = ex.latency_s = 0
        if kind == "khatian":
            khatian = data
        elif kind == "deed" and not data.is_draft:
            registered_deed = data

    if khatian:
        land.district = khatian.location.district
        land.upazila = khatian.location.upazila
        land.mouza = khatian.location.mouza
        deed_dags = (
            {plot.dag_no for plot in registered_deed.schedule_plots} if registered_deed else set()
        )
        land.dag_no = next(
            (plot.dag_no for plot in khatian.plots if plot.dag_no in deed_dags),
            khatian.plots[0].dag_no if khatian.plots else "",
        )
        land.khatian_no = khatian.khatian_no
    db.flush()
    from app.services.land_case import load_land_case

    case = load_land_case(db, land_id)
    rules = run_rules(case)
    result = assess(case, rules)
    result.actions = next_actions(case, rules, result)
    assessment = db.scalars(
        select(LandAssessment)
        .where(LandAssessment.land_id == land_id)
        .order_by(LandAssessment.created_at.desc())
        .limit(1)
    ).first()
    if assessment is None:
        assessment = LandAssessment(land_id=land_id)
        db.add(assessment)
    assessment.engine_version = result.engine_version
    assessment.risk_level = result.risk_level
    assessment.result = result.model_dump(mode="json")
    db.commit()
    return land_id, result.risk_level, seeded


def seed_historical_deeds(
    db: Session, storage, land_id: uuid.UUID | None = None, case_id: str = "00026"
) -> None:
    """Add repeatable synthetic prior deed pages to a demo land."""
    import copy

    land_id = land_id or uuid.uuid5(uuid.NAMESPACE_URL, f"jomiguard-demo-{case_id}")
    folder = ROOT / f"case_{case_id}"
    template = json.loads((folder / "deed.json").read_text(encoding="utf-8"))
    if case_id == "00001":
        next_seller = (template.get("sellers") or [{"name": "মোঃ কামাল উদ্দিন"}])[0]["name"]
        entries = (("1985", "8501", "মোঃ আব্দুল হক", next_seller),)
    else:
        entries = (
            ("1992", "9201", "আব্দুল কাদের", "মোঃ করিম উদ্দিন"),
            ("2003", "0302", "মোঃ করিম উদ্দিন", "রহিমা বেগম"),
        )
    for year, number, seller, buyer in entries:
        doc_id = uuid.uuid5(land_id, f"historical-deed-{year}")
        if db.get(Document, doc_id) is not None:
            continue
        raw = copy.deepcopy(template)
        raw["deed_no"] = number
        raw["deed_year"] = year
        raw["registration_date"] = f"{year}-06-15"
        raw["registration_date_text"] = f"১৫/০৬/{year}"
        raw["sellers"] = [{**raw["sellers"][0], "name": seller}]
        raw["buyers"] = [{**raw["buyers"][0], "name": buyer}]
        normalized = normalize_document(DeedData.model_validate(raw))
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="1200" '
            'viewBox="0 0 900 1200"><rect width="100%" height="100%" fill="#fff"/>'
            '<g fill="#18201c" font-family="sans-serif" font-size="32">'
            '<text x="70" y="100">নমুনা পুরোনো বিক্রয় দলিল</text>'
            f'<text x="70" y="190">দলিল নম্বর: {number}</text>'
            f'<text x="70" y="250">তারিখ: ১৫/০৬/{year}</text>'
            f'<text x="70" y="330">দাতা: {seller}</text>'
            f'<text x="70" y="390">গ্রহীতা: {buyer}</text>'
            f'<text x="70" y="470">দাগ: {normalized.doc.schedule_plots[0].dag_no}</text>'
            f'<text x="70" y="530">জমি: {normalized.doc.transferred_area_text}</text>'
            '<text x="70" y="650">সব নাম ও সংখ্যা নমুনা</text>'
            "</g></svg>"
        ).encode()
        key = f"demo/{case_id}/historical-{year}.svg"
        storage.upload(key, svg, "image/svg+xml")
        doc = Document(
            id=doc_id,
            land_id=land_id,
            owner_id=db.scalar(select(User.id).where(User.username == settings.admin_username)),
            doc_type=DocType.deed,
            detected_doc_type=DocType.deed,
            file_key=key,
            original_filename=f"synthetic-historical-deed-{year}.svg",
            content_sha256=hashlib.sha256(svg).hexdigest(),
            status=DocStatus.done,
            current_step=DocStep.finished,
            finished_at=datetime.now(UTC),
        )
        db.add(doc)
        db.add(
            DocumentAuditEvent(
                document_id=doc_id,
                event="uploaded",
                actor="seed",
                details={"source_type": "user_upload"},
            )
        )
        db.add(
            Extraction(
                document_id=doc_id,
                extractor="seed",
                created_by="seed",
                status=ExtractionStatus.ok,
                data=normalized.doc.model_dump(mode="json"),
                warnings=[w.__dict__ for w in normalized.warnings],
                field_flags={},
                cost_usd=0,
                latency_s=0,
            )
        )
    db.flush()
    from app.services.land_case import load_land_case

    case = load_land_case(db, land_id)
    rules = run_rules(case)
    result = assess(case, rules)
    result.actions = next_actions(case, rules, result)
    assessment = db.scalars(
        select(LandAssessment)
        .where(LandAssessment.land_id == land_id)
        .order_by(LandAssessment.created_at.desc())
        .limit(1)
    ).first()
    if assessment is None:
        assessment = LandAssessment(land_id=land_id)
        db.add(assessment)
    assessment.engine_version = result.engine_version
    assessment.risk_level = result.risk_level
    assessment.result = result.model_dump(mode="json")
    db.commit()


def reset(
    cases: list[tuple[str, Path]] | None = None,
    db: Session | None = None,
    storage=None,
    cache_dir: Path | None = None,
):
    seed_guardian_demo = cases is None
    owned = db is None
    db = db or SessionLocal()
    storage = storage or get_storage()
    storage.ensure_bucket()
    cases = cases or [(n, ROOT / f"case_{n}") for n in CASE_IDS]
    try:
        for case_id, folder in cases:
            land_id, risk, seeded = seed_case(
                case_id, folder, db, storage, cache_dir or Path(settings.llm_cache_dir)
            )
            fallback = f" | seed fallback: {', '.join(seeded)}" if seeded else ""
            print(f"{case_id}: {land_id} | {risk} | /cases/{land_id}{fallback}")
        if seed_guardian_demo:
            seed_historical_deeds(
                db,
                storage,
            )
            seed_historical_deeds(db, storage, case_id="00001")
            from app.scripts.guardian_seed import seed_guardian

            seed_guardian(db)
            from app.scripts.escrow_seed import seed_escrow

            deal_id = seed_escrow(db)
            if deal_id:
                print(f"escrow 00026: {deal_id} | /escrow/demo-00026")
    finally:
        if owned:
            db.close()


def main():
    reset()


if __name__ == "__main__":
    main()
