"""Keep the public demo usable: prepared sample cases stay unchanged, and live work is capped.

Prepared samples are the lands seeded by app.scripts.demo_reset; their documents are stored
under the "demo/" key prefix. Limits count rows from the last hour in the database, so they
hold across API workers without Redis.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Document, Land, SatelliteCheck

SATELLITE_PER_HOUR = 5
UPLOADS_PER_HOUR = 40

SAMPLE_LOCKED_BN = (
    "এটি প্রস্তুত নমুনা কেস, তাই এখানে কিছু বদলানো যায় না। নিজে চেষ্টা করতে নমুনা ডেটা "
    "পাতা থেকে এক ক্লিকে নিজের নতুন কেস তৈরি করুন।"
)
SATELLITE_LIMIT_BN = (
    f"এক ঘণ্টায় সর্বোচ্চ {SATELLITE_PER_HOUR}টি স্যাটেলাইট যাচাই চালানো যায়। কিছুক্ষণ পরে আবার "
    "চেষ্টা করুন; ততক্ষণ নমুনা কেসগুলোর ফল দেখুন।"
)
UPLOAD_LIMIT_BN = "এক ঘণ্টায় অনেক বেশি নথি upload হয়েছে। কিছুক্ষণ পরে আবার চেষ্টা করুন।"


def is_prepared_sample(db: Session, land_id: uuid.UUID | None) -> bool:
    if land_id is None:
        return False
    found = db.scalar(
        select(Document.id)
        .where(Document.land_id == land_id, Document.file_key.like("demo/%"))
        .limit(1)
    )
    return found is not None


def _since() -> datetime:
    return datetime.now(UTC) - timedelta(hours=1)


def satellite_checks_last_hour(db: Session, user_id: uuid.UUID) -> int:
    q = (
        select(func.count())
        .select_from(SatelliteCheck)
        .join(Land, Land.id == SatelliteCheck.land_id)
        .where(Land.owner_id == user_id, SatelliteCheck.created_at >= _since())
    )
    return db.scalar(q) or 0


def uploads_last_hour(db: Session, user_id: uuid.UUID) -> int:
    q = (
        select(func.count())
        .select_from(Document)
        .where(Document.owner_id == user_id, Document.created_at >= _since())
    )
    return db.scalar(q) or 0


def satellite_allowed(db: Session, user_id: uuid.UUID) -> bool:
    return satellite_checks_last_hour(db, user_id) < SATELLITE_PER_HOUR


def upload_allowed(db: Session, user_id: uuid.UUID, files: int = 1) -> bool:
    return uploads_last_hour(db, user_id) + files <= UPLOADS_PER_HOUR
