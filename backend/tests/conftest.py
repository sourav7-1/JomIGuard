import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core.auth import SESSION_COOKIE, hash_password, issue_session
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Document, Land, User
from app.services.storage import get_storage

assert settings.test_database_url != settings.database_url, "tests must not use the main DB"

engine = create_engine(settings.test_database_url)
TestSession = sessionmaker(engine, expire_on_commit=False)
TEST_ADMIN_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")


@event.listens_for(TestSession.class_, "before_flush")
def assign_test_owner(session, *_):
    for item in session.new:
        if isinstance(item, (Land, Document)) and item.owner_id is None:
            item.owner_id = TEST_ADMIN_ID


class FakeStorage:
    def __init__(self):
        self.objects: dict[str, tuple[bytes, str]] = {}

    def ensure_bucket(self) -> None:
        pass

    def upload(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = (data, content_type)

    def download(self, key: str) -> bytes:
        return self.objects[key][0]


@pytest.fixture(scope="session", autouse=True)
def tables():
    Base.metadata.drop_all(engine)  # clear leftovers from an aborted run
    Base.metadata.create_all(engine)
    with TestSession.begin() as db:
        db.add(
            User(
                id=TEST_ADMIN_ID,
                username=settings.admin_username,
                password_hash=hash_password(settings.admin_password.get_secret_value()),
            )
        )
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def storage():
    return FakeStorage()


@pytest.fixture
def client(storage):
    def test_db():
        with TestSession() as db:
            yield db

    app.dependency_overrides[get_db] = test_db
    app.dependency_overrides[get_storage] = lambda: storage
    with TestClient(app) as c:
        c.cookies.set(SESSION_COOKIE, issue_session(TEST_ADMIN_ID))
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def anonymous_client(storage):
    def test_db():
        with TestSession() as db:
            yield db

    app.dependency_overrides[get_db] = test_db
    app.dependency_overrides[get_storage] = lambda: storage
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
