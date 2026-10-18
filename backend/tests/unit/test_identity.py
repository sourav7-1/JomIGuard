import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from conftest import TestSession
from scenario_loader import load_scenario

from app.models import (
    DocStatus,
    DocType,
    Document,
    Extraction,
    ExtractionStatus,
    IdentityVerification,
    SellerLink,
)
from app.schemas.land_case import IdentityCaseResult
from app.services.rules import Status, run_rules

SCENARIO = Path(__file__).parents[1] / "scenarios/01_demo_area_exceeds"


def _land_with_case(client):
    case, _ = load_scenario(SCENARIO)
    land_id = uuid.UUID(client.post("/lands", json={"mouza": "চাঁদশী", "dag_no": "305"}).json()["id"])
    with TestSession() as db:
        for item in case.documents:
            doc_id = uuid.uuid4()
            doc_type = DocType(item.doc_type)
            doc = Document(
                id=doc_id,
                land_id=land_id,
                doc_type=doc_type,
                detected_doc_type=doc_type,
                status=DocStatus.done,
                file_key=f"{doc_id}/case.png",
                original_filename="case.png",
            )
            db.add(doc)
            db.flush()
            db.add(
                Extraction(
                    document_id=doc_id,
                    extractor="seed",
                    status=ExtractionStatus.ok,
                    data=item.data.model_dump(mode="json"),
                    warnings=[],
                    field_flags={},
                )
            )
        db.commit()
    return land_id, case


def _create_link(client, land_id, seller_name):
    response = client.post(
        f"/lands/{land_id}/seller-links", json={"seller_name_on_deed": seller_name}
    )
    assert response.status_code == 201, response.text
    return response.json()["url"].split("/")[-1]


def test_seller_link_hash_consent_single_use_and_only_result_stored(client):
    land_id, case = _land_with_case(client)
    seller = case.proposed_deed.data.sellers[0]
    token = _create_link(client, land_id, seller.name)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with TestSession() as db:
        link = db.query(SellerLink).filter_by(token_hash=token_hash).one()
        assert token_hash == link.token_hash and token not in link.token_hash

    details = client.get(f"/verify/{token}")
    assert details.status_code == 200
    assert set(details.json()) == {"mouza", "dag_no", "message_bn", "escrow_agreement_requested"}
    assert details.json()["escrow_agreement_requested"] is False
    assert (
        client.post(
            f"/verify/{token}/complete",
            json={
                "name": seller.name,
                "father_name": seller.father_or_husband_name,
                "outcome": "verified",
            },
        ).status_code
        == 409
    )
    assert client.post(f"/verify/{token}/consent", json={"consent": True}).status_code == 200
    result = client.post(
        f"/verify/{token}/complete",
        json={
            "name": seller.name,
            "father_name": seller.father_or_husband_name,
            "outcome": "verified",
        },
    )
    assert result.status_code == 200 and result.json()["status"] == "verified"
    assert (
        client.post(
            f"/verify/{token}/complete",
            json={
                "name": seller.name,
                "father_name": seller.father_or_husband_name,
                "outcome": "verified",
            },
        ).status_code
        == 410
    )
    with TestSession() as db:
        saved = db.query(IdentityVerification).filter_by(land_id=land_id).one()
        assert saved.name_bn_as_per_nid == seller.name
        assert saved.father_name_as_per_nid == seller.father_or_husband_name
    view = client.get(f"/lands/{land_id}/case-view").json()
    [verification] = view["identity_verifications"]
    assert verification["status"] == "verified"
    assessment = client.post(f"/lands/{land_id}/assess").json()
    assert assessment["identity_verifications"][0]["id"] == verification["id"]
    assert client.delete(f"/verify/{token}").status_code == 204
    assert client.get(f"/lands/{land_id}/case-view").json()["identity_verifications"] == []


def test_seller_link_expired_returns_410(client):
    land_id, case = _land_with_case(client)
    token = _create_link(client, land_id, case.proposed_deed.data.sellers[0].name)
    with TestSession.begin() as db:
        link = (
            db.query(SellerLink)
            .filter_by(token_hash=hashlib.sha256(token.encode()).hexdigest())
            .one()
        )
        link.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    assert client.get(f"/verify/{token}").status_code == 410
    assert client.post(f"/verify/{token}/consent", json={"consent": True}).status_code == 410


def test_identity_rules_match_mismatch_unverified_and_scenario_skip():
    case, _ = load_scenario(SCENARIO)
    seller = case.proposed_deed.data.sellers[0]
    identity_rule = ["seller_identity"]
    skipped = run_rules(case, identity_rule).results[0]
    assert skipped.status == Status.skipped

    unverified = case.model_copy(update={"identity": []})
    [finding] = run_rules(unverified, identity_rule).findings
    assert finding.code == "seller_identity_unverified" and finding.status == Status.warn

    verified_match = case.model_copy(
        update={
            "identity": [
                IdentityCaseResult(
                    party="seller",
                    seller_name_on_deed=seller.name,
                    status="verified",
                    name_bn_as_per_nid=seller.name,
                    father_name_as_per_nid=seller.father_or_husband_name,
                )
            ]
        }
    )
    assert not run_rules(verified_match, identity_rule).findings
    assert run_rules(verified_match, identity_rule).passed[0].rule_id == "seller_identity"

    mismatch = verified_match.model_copy(
        update={
            "identity": [
                IdentityCaseResult(
                    party="seller",
                    seller_name_on_deed=seller.name,
                    status="verified",
                    name_bn_as_per_nid="করিম উদ্দিন",
                    father_name_as_per_nid="রহমান",
                )
            ]
        }
    )
    [finding] = run_rules(mismatch, identity_rule).findings
    assert finding.code == "seller_nid_name_mismatch" and finding.status == Status.bad


def test_buyer_identity_requires_consent_and_rejects_unrequested_fields(client):
    before = {row["id"] for row in client.get("/me/verification").json()}
    for extra in (
        {"nid_number": "not-accepted"},
        {"nid_image": "base64-data"},
        {"phone": "not-accepted"},
    ):
        response = client.post(
            "/me/verification",
            json={
                "name": "নমুনা নাম",
                "father_name": "নমুনা পিতা",
                "outcome": "verified",
                "consent": True,
                **extra,
            },
        )
        assert response.status_code == 422
    response = client.post(
        "/me/verification",
        json={
            "name": "নমুনা নাম",
            "father_name": "নমুনা পিতা",
            "outcome": "verified",
            "consent": True,
        },
    )
    assert response.status_code == 201
    assert response.json()["party"] == "buyer"
    verification_id = response.json()["id"]
    assert {row["id"] for row in client.get("/me/verification").json()} == before | {
        verification_id
    }
    assert client.delete(f"/me/verification/{verification_id}").status_code == 204
    assert {row["id"] for row in client.get("/me/verification").json()} == before
