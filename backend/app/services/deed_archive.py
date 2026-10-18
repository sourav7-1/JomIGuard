"""Field-by-field comparison of deed values already extracted from source documents."""

import hashlib

from minio.error import S3Error


def integrity_status(document, storage) -> str:
    try:
        stored_bytes = storage.download(document.file_key)
    except KeyError:  # in-memory storage used by tests
        return "ফাইল পাওয়া যায়নি"
    except S3Error as exc:
        if exc.code == "NoSuchKey":
            return "ফাইল পাওয়া যায়নি"
        raise
    if not document.content_sha256:
        return "fingerprint নেই"
    current = hashlib.sha256(stored_bytes).hexdigest()
    return "কপি অপরিবর্তিত" if current == document.content_sha256 else "কপি বদলেছে"


_FIELDS = (
    ("deed_no", "দলিল নম্বর", "deed_no"),
    ("date", "দলিলের তারিখ", "registration_date"),
    ("deed_type", "দলিলের ধরন", "deed_type"),
    ("sellers", "দাতা", "sellers"),
    ("buyers", "গ্রহীতা", "buyers"),
    ("schedule_location", "মৌজা", "schedule_location"),
    ("schedule_plots", "দাগ ও জমির পরিমাণ", "schedule_plots"),
    ("transferred_area_text", "হস্তান্তরিত জমি", "transferred_area_text"),
)


def _value(data: dict, field: str):
    if field == "date":
        return (
            data.get("registration_date")
            or data.get("registration_date_text")
            or data.get("deed_year")
        )
    if field in ("sellers", "buyers"):
        return [person.get("name") for person in data.get(field, [])]
    if field == "schedule_location":
        location = data.get(field) or {}
        return location.get("mouza")
    if field == "schedule_plots":
        return [
            {"dag_no": plot.get("dag_no"), "area_text": plot.get("area_text")}
            for plot in data.get(field, [])
        ]
    return data.get(field)


def compare_deeds(current: dict, previous: dict) -> list[dict]:
    """Return source-linked values; no title or authenticity conclusion is inferred."""
    return [
        {
            "key": key,
            "label_bn": label,
            "current": _value(current, field),
            "previous": _value(previous, field),
            "current_field": field,
            "previous_field": field,
        }
        for key, label, field in _FIELDS
    ]
