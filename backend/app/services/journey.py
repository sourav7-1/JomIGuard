"""Journey state for one plot: which of the 8 steps are done, what blocks the next one, and
what the paper check could not cover. One function feeds the case page, the dashboard card
and the PDF headline, so they never disagree.

Safety rule (CLAUDE.md: never imply land is fine): when any document is unread or still being
read, the assessment is stale, or checks were skipped, the low-risk headline is replaced by
an "incomplete" one. The risk level itself is never changed.
"""

import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Document,
    EscrowDeal,
    Extraction,
    GuardedLand,
    IdentityVerification,
    Land,
    LandAssessment,
    SatelliteCheck,
)
from app.schemas.journey import CaseSummary, Journey, JourneyStep
from app.services.extraction.fallback import TESSERACT
from app.services.normalize import to_bangla_digits

BANGLA_LETTER = re.compile("[ঀ-৿]")


def is_listed(
    district: str | None, mouza: str | None, dag_no: str | None, upazila: str | None = ""
) -> bool:
    """A real-looking case: district and dag set, a Bangla mouza, no "??" from a bad encoding."""
    names = f"{mouza or ''}{upazila or ''}"
    return bool(
        (district or "").strip()
        and (dag_no or "").strip()
        and BANGLA_LETTER.search(mouza or "")
        and "??" not in names
    )


INCOMPLETE_HEADLINE_BN = "সব কাগজ মেলানো যায়নি: {reason}"
PHASES = {1: "before", 2: "before", 3: "before", 4: "before", 5: "before",
          6: "during", 7: "during", 8: "after"}  # fmt: skip
KEYS = {1: "location", 2: "documents", 3: "paper", 4: "ground", 5: "report",
        6: "seller", 7: "escrow", 8: "guardian"}  # fmt: skip


def _n(value: int) -> str:
    return to_bangla_digits(str(value))


@dataclass
class JourneyInput:
    doc_statuses: list[str] = field(default_factory=list)  # DocStatus values
    ocr_limited: int = 0  # documents whose latest read came from the Tesseract fallback
    has_geometry: bool = False
    assessment: dict | None = None  # stored Assessment JSON (risk_level, coverage, actions)
    assessment_stale: bool = False
    satellite_status: str | None = None  # latest check: pending | ok | failed
    seller_verified: bool = False
    escrow_deal_id: str | None = None
    guarded: bool = False


def incomplete_reasons(inp: JourneyInput) -> list[str]:
    failed = sum(s == "failed" for s in inp.doc_statuses)
    pending = sum(s in ("uploaded", "processing") for s in inp.doc_statuses)
    reasons = []
    if failed:
        reasons.append(f"{_n(failed)}টি কাগজ পড়া যায়নি")
    if pending:
        reasons.append(f"{_n(pending)}টি কাগজ এখনো পড়া হচ্ছে")
    if inp.ocr_limited:
        reasons.append(f"{_n(inp.ocr_limited)}টি কাগজ সীমিত পাঠে (OCR) পড়া; কিছু তথ্য বাদ থাকতে পারে")
    if inp.assessment is not None and inp.assessment_stale:
        reasons.append("কাগজের তথ্য বদলেছে, আবার যাচাই করা হয়নি")
    coverage = (inp.assessment or {}).get("coverage") or {}
    skipped = len(coverage.get("checks_skipped") or [])
    if skipped:
        reasons.append(f"{_n(skipped)}টি পরীক্ষা চালানো যায়নি")
    missing = coverage.get("documents_missing_bn") or []
    if missing:
        reasons.append("কেসে নেই: " + ", ".join(missing))
    return reasons


def build_journey(inp: JourneyInput) -> Journey:
    statuses = inp.doc_statuses
    failed = sum(s == "failed" for s in statuses)
    pending = sum(s in ("uploaded", "processing") for s in statuses)
    read = sum(s == "done" for s in statuses)
    reasons = incomplete_reasons(inp)

    s: dict[int, tuple[str, str]] = {}
    s[1] = ("done", "") if inp.has_geometry else ("action", "মানচিত্রে প্লটের সীমানা আঁকুন")
    if not statuses:
        s[2] = ("action", "জমির কাগজ upload করুন")
    elif failed:
        s[2] = ("action", f"{_n(failed)}টি কাগজ পড়া যায়নি: আবার চেষ্টা করুন বা নতুন ছবি দিন")
    elif pending:
        s[2] = ("waiting", f"{_n(pending)}টি কাগজ পড়া হচ্ছে")
    else:
        s[2] = ("done", "")

    if not read:
        s[3] = ("locked", "আগে ধাপ ২-এ কাগজ জমা দিন; পড়া হলে মেলানো যাবে")
    elif s[2][0] == "waiting":
        s[3] = ("waiting", "সব কাগজ পড়া হলে মেলানো হবে")
    elif inp.assessment is None:
        s[3] = ("action", "কাগজগুলো মিলিয়ে দেখুন")
    elif inp.assessment_stale:
        s[3] = ("action", "কাগজের তথ্য বদলেছে: আবার যাচাই করুন")
    elif failed:
        s[3] = ("action", f"{_n(failed)}টি কাগজ পড়া যায়নি, তাই সব পরীক্ষা চালানো যায়নি")
    else:
        s[3] = ("done", "")

    if not inp.has_geometry:
        s[4] = ("locked", "আগে ধাপ ১-এ প্লটের সীমানা আঁকুন")
    elif inp.satellite_status == "ok":
        s[4] = ("done", "")
    elif inp.satellite_status == "pending":
        s[4] = ("waiting", "স্যাটেলাইট যাচাই চলছে")
    else:
        s[4] = ("action", "স্যাটেলাইট যাচাই চালান")

    if s[3][0] != "done":
        s[5] = ("locked", "আগে ধাপ ৩-এ কাগজ যাচাই শেষ করুন")
    elif s[4][0] != "done":
        s[5] = ("action", "PDF নেওয়া যায়; মাটি যাচাই এখনো বাকি")
    else:
        s[5] = ("done", "")

    s[6] = ("done", "") if inp.seller_verified else ("todo", "বিক্রেতার পরিচয় যাচাই করুন")
    s[7] = ("done", "") if inp.escrow_deal_id else ("todo", "বায়না এসক্রো শুরু করুন")
    s[8] = ("done", "") if inp.guarded else ("todo", "কেনার পরে খতিয়ান নজরদারিতে রাখুন")

    steps = [JourneyStep(n=n, key=KEYS[n], phase=PHASES[n], status=st, note_bn=note)
             for n, (st, note) in sorted(s.items())]  # fmt: skip
    return Journey(
        steps=steps,
        progress_done=sum(st.status == "done" for st in steps[:5]),
        incomplete_reasons_bn=reasons,
        next_action_bn=_next_action(inp, steps),
        escrow_deal_id=inp.escrow_deal_id,
    )


def _next_action(inp: JourneyInput, steps: list[JourneyStep]) -> str | None:
    # a blocking document problem comes first; then the assessment's own first open action
    if steps[1].status == "action":
        return steps[1].note_bn
    actions = (inp.assessment or {}).get("actions") or []
    open_actions = [a for a in actions if not a.get("done")]
    if open_actions and not inp.assessment_stale:
        return open_actions[0].get("text_bn")
    first = next((st for st in steps[:5] if st.status in ("action", "locked")), None)
    return first.note_bn if first else None


def safe_headline(assessment: dict, journey: Journey) -> str:
    """The headline to show: a low-risk headline never survives an incomplete check."""
    if assessment.get("risk_level") == "low" and journey.incomplete_reasons_bn:
        return INCOMPLETE_HEADLINE_BN.format(reason=journey.incomplete_reasons_bn[0])
    return assessment["headline_bn"]


# --- loading the input from the database ---


def _aware(dt: datetime | None) -> datetime | None:
    return dt.replace(tzinfo=UTC) if dt is not None and dt.tzinfo is None else dt


def journey_input(db: Session, land: Land, assessment_row: LandAssessment | None) -> JourneyInput:
    # ponytail: ~6 small queries per land; the dashboard lists a user's few dozen lands at most
    docs = db.scalars(select(Document).where(Document.land_id == land.id)).all()
    rows = db.execute(
        select(Extraction.document_id, Extraction.extractor, Extraction.created_at)
        .where(Extraction.document_id.in_([d.id for d in docs]))
        .order_by(Extraction.created_at.desc())
    ).all() if docs else []  # fmt: skip
    latest_by_doc: dict = {}
    for doc_id, extractor, _ in rows:
        latest_by_doc.setdefault(doc_id, extractor)
    done_ids = {d.id for d in docs if str(d.status) == "done"}
    ocr_limited = sum(latest_by_doc.get(i) == TESSERACT for i in done_ids)
    stale = False
    if assessment_row is not None and rows:
        stale = _aware(rows[0].created_at) > _aware(assessment_row.created_at)
    sat = db.scalars(
        select(SatelliteCheck.status)
        .where(SatelliteCheck.land_id == land.id)
        .order_by(SatelliteCheck.created_at.desc())
        .limit(1)
    ).first()
    verified = db.scalars(
        select(IdentityVerification.id).where(
            IdentityVerification.land_id == land.id,
            IdentityVerification.party == "seller",
            IdentityVerification.status == "verified",
        )
    ).first()
    deal = db.scalars(
        select(EscrowDeal.id)
        .where(EscrowDeal.land_id == land.id, EscrowDeal.archived.is_(False))
        .order_by(EscrowDeal.created_at.desc())
        .limit(1)
    ).first()
    guarded = db.scalars(
        select(GuardedLand.id).where(
            GuardedLand.user_id == land.owner_id,
            GuardedLand.district == land.district,
            GuardedLand.mouza == land.mouza,
            GuardedLand.dag_no == land.dag_no,
        )
    ).first()
    return JourneyInput(
        doc_statuses=[str(d.status) for d in docs],
        ocr_limited=ocr_limited,
        has_geometry=bool(land.geometry),
        assessment=assessment_row.result if assessment_row is not None else None,
        assessment_stale=stale,
        satellite_status=sat,
        seller_verified=verified is not None,
        escrow_deal_id=str(deal) if deal else None,
        guarded=guarded is not None,
    )


def latest_assessment_row(db: Session, land_id: uuid.UUID) -> LandAssessment | None:
    return db.scalars(
        select(LandAssessment)
        .where(LandAssessment.land_id == land_id)
        .order_by(LandAssessment.created_at.desc())
        .limit(1)
    ).first()


def case_summary(db: Session, land: Land) -> CaseSummary:
    row = latest_assessment_row(db, land.id)
    journey = build_journey(journey_input(db, land, row))
    last_doc = db.scalar(select(func.max(Document.created_at)).where(Document.land_id == land.id))
    times = [land.created_at, row.created_at if row else None, last_doc]
    updated = max(_aware(t) for t in times if t is not None)
    return CaseSummary(
        risk_level=row.risk_level if row is not None else None,
        complete=row is not None and not journey.incomplete_reasons_bn,
        progress_done=journey.progress_done,
        updated_at=updated,
        next_action_bn=journey.next_action_bn,
        listed=is_listed(land.district, land.mouza, land.dag_no, land.upazila),
    )
