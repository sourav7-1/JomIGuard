import hashlib
from types import SimpleNamespace
from unittest.mock import Mock

from minio.error import S3Error

from app.scripts import backfill_document_fingerprints as script


def test_backfill_hashes_available_objects_and_skips_missing(monkeypatch):
    found = SimpleNamespace(file_key="found", content_sha256=None)
    missing = SimpleNamespace(file_key="missing", content_sha256=None)
    db = Mock()
    db.__enter__ = Mock(return_value=db)
    db.__exit__ = Mock(return_value=False)
    db.scalars.return_value.all.return_value = [found, missing]
    storage = Mock()
    storage.download.side_effect = [
        b"synthetic",
        S3Error(None, "NoSuchKey", "missing", "x", "x", "x"),
    ]
    monkeypatch.setattr(script, "SessionLocal", lambda: db)
    monkeypatch.setattr(script, "get_storage", lambda: storage)

    assert script.backfill() == (1, 1)
    assert found.content_sha256 == hashlib.sha256(b"synthetic").hexdigest()
    assert missing.content_sha256 is None
    db.commit.assert_called_once()
