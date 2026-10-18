import json
import shutil
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from conftest import TestSession
from sqlalchemy import func, select

from app.models import Document, Extraction, IdentityVerification, Land, LandAssessment, SellerLink
from app.scripts.demo_reset import seed_case


def test_reset_seeds_a_tiny_synthetic_case_idempotently(tmp_path, storage):
    source = Path(__file__).parents[3] / "data/synthetic/cases/case_00026"
    case = tmp_path / "tiny"
    case.mkdir()
    for document in ("khatian", "deed"):
        for suffix in ("png", "json"):
            shutil.copy(source / f"{document}.{suffix}", case / f"{document}.{suffix}")
    (case / "case.json").write_text(
        json.dumps({"case_id": "tiny", "documents": ["khatian", "deed"]}), encoding="utf-8"
    )
    cache = tmp_path / "empty-cache"
    cache.mkdir()

    with TestSession() as db:
        first = seed_case("tiny", case, db, storage, cache)
        land_id = uuid.uuid5(uuid.NAMESPACE_URL, "jomiguard-demo-tiny")
        deed = json.loads((case / "deed.json").read_text(encoding="utf-8"))
        khatian = json.loads((case / "khatian.json").read_text(encoding="utf-8"))
        deed_dags = {plot["dag_no"] for plot in deed["schedule_plots"]}
        expected_dag = next(
            (plot["dag_no"] for plot in khatian["plots"] if plot["dag_no"] in deed_dags),
            khatian["plots"][0]["dag_no"],
        )
        db.add(
            SellerLink(
                land_id=land_id,
                seller_name_on_deed="নমুনা বিক্রেতা",
                token_hash="a" * 64,
                expires_at=datetime.now(UTC) + timedelta(days=7),
            )
        )
        db.add(
            IdentityVerification(
                land_id=land_id,
                user_id=None,
                party="seller",
                seller_name_on_deed="নমুনা বিক্রেতা",
                status="verified",
                name_bn_as_per_nid="নমুনা বিক্রেতা",
                father_name_as_per_nid="নমুনা পিতা",
                provider="mock",
                provider_ref="test-ref",
                consent_at=datetime.now(UTC),
                consent_version="test",
                verified_at=datetime.now(UTC),
            )
        )
        db.flush()
        second = seed_case("tiny", case, db, storage, cache)
        assert first == second
        assert db.get(Land, land_id).dag_no == expected_dag
        assert (
            db.scalar(
                select(func.count())
                .select_from(IdentityVerification)
                .where(IdentityVerification.land_id == land_id)
            )
            == 0
        )
        assert (
            db.scalar(
                select(func.count()).select_from(SellerLink).where(SellerLink.land_id == land_id)
            )
            == 0
        )
        assert db.scalar(select(func.count()).select_from(Land).where(Land.id == land_id)) == 1
        assert (
            db.scalar(select(func.count()).select_from(Document).where(Document.land_id == land_id))
            == 2
        )
        document_id = uuid.uuid5(land_id, "khatian")
        assert (
            db.scalar(
                select(func.count())
                .select_from(Extraction)
                .where(Extraction.document_id == document_id)
            )
            == 1
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(LandAssessment)
                .where(LandAssessment.land_id == land_id)
            )
            == 1
        )
        assert (
            db.scalar(select(Extraction.extractor).where(Extraction.document_id == document_id))
            == "seed"
        )
        assert len(storage.objects) == 2
