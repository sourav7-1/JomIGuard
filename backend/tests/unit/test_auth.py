import uuid

from conftest import TEST_ADMIN_ID, TestSession

from app.api.auth import clear_login_attempts
from app.core.auth import SESSION_COOKIE, hash_password, issue_session, session_user_id
from app.core.config import settings
from app.models import Land, User


def credentials(password=None):
    return {
        "username": settings.admin_username,
        "password": password or settings.admin_password.get_secret_value(),
    }


def test_login_sets_signed_http_only_session_cookie(client):
    response = client.post("/auth/login", json=credentials())
    assert response.status_code == 200
    assert response.json() == {"id": str(TEST_ADMIN_ID), "username": settings.admin_username}
    cookie = response.headers["set-cookie"].lower()
    assert SESSION_COOKIE in cookie and "httponly" in cookie and "samesite=lax" in cookie
    assert "max-age=604800" in cookie
    assert "password_hash" not in response.text


def test_login_marks_cookie_secure_when_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "cookie_secure", True)
    response = client.post("/auth/login", json=credentials())
    assert "; secure" in response.headers["set-cookie"].lower()


def test_session_signature_and_seven_day_expiry():
    token = issue_session(TEST_ADMIN_ID, now=100)
    assert session_user_id(token, now=101) == TEST_ADMIN_ID
    assert session_user_id(token + "x", now=101) is None
    assert session_user_id(token, now=100 + 7 * 24 * 60 * 60) is None


def test_wrong_password_returns_bangla_401(anonymous_client):
    response = anonymous_client.post("/auth/login", json=credentials("wrong"))
    assert response.status_code == 401
    assert "সঠিক নয়" in response.json()["detail"]


def test_fifth_failed_login_is_allowed_and_sixth_is_rate_limited(anonymous_client):
    clear_login_attempts()
    for _ in range(5):
        assert anonymous_client.post("/auth/login", json=credentials("wrong")).status_code == 401
    response = anonymous_client.post("/auth/login", json=credentials("wrong"))
    assert response.status_code == 429


def test_protected_route_rejects_missing_cookie(anonymous_client):
    response = anonymous_client.get("/lands")
    assert response.status_code == 401


def test_health_and_openapi_remain_public(anonymous_client):
    assert anonymous_client.get("/health").status_code == 200
    assert anonymous_client.get("/openapi.json").status_code == 200


def test_user_cannot_see_another_users_land(client):
    owner_id = uuid.uuid4()
    with TestSession.begin() as db:
        db.add(User(id=owner_id, username="other", password_hash=hash_password("unused")))
        db.flush()
        land = Land(
            owner_id=owner_id, district="", upazila="", mouza="private", dag_no="9", khatian_no=""
        )
        db.add(land)
        db.flush()
        land_id = land.id
    assert client.get(f"/lands/{land_id}").status_code == 404
    assert all(item["id"] != str(land_id) for item in client.get("/lands").json())
