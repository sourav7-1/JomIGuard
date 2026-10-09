import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.services.storage import get_storage

assert settings.test_database_url != settings.database_url, "tests must not use the main DB"

engine = create_engine(settings.test_database_url)
TestSession = sessionmaker(engine, expire_on_commit=False)


class FakeStorage:
    def __init__(self):
        self.objects: dict[str, tuple[bytes, str]] = {}

    def ensure_bucket(self) -> None:
        pass

    def upload(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = (data, content_type)


@pytest.fixture(scope="session", autouse=True)
def tables():
    Base.metadata.drop_all(engine)  # clear leftovers from an aborted run
    Base.metadata.create_all(engine)
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
        yield c
    app.dependency_overrides.clear()
