import base64
import hashlib
import hmac
import secrets
import time
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal, get_db
from app.models import User

SESSION_COOKIE = "jomiguard_session"
SESSION_SECONDS = 7 * 24 * 60 * 60
PASSWORD_ITERATIONS = 310_000
Db = Annotated[Session, Depends(get_db)]


def _secret() -> bytes:
    value = settings.session_secret.get_secret_value()
    if value == "change_me" or len(value.encode()) < 32:
        raise RuntimeError("SESSION_SECRET must be at least 32 characters")
    return value.encode()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ITERATIONS)
    encoded_salt = base64.b64encode(salt).decode()
    encoded_digest = base64.b64encode(digest).decode()
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${encoded_salt}${encoded_digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt, expected = stored.split("$")
        if algorithm != "pbkdf2_sha256" or not 100_000 <= int(iterations) <= 1_000_000:
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), base64.b64decode(salt, validate=True), int(iterations)
        )
        return hmac.compare_digest(actual, base64.b64decode(expected, validate=True))
    except (ValueError, TypeError):
        return False


def issue_session(user_id: UUID, now: int | None = None) -> str:
    expiry = (int(time.time()) if now is None else now) + SESSION_SECONDS
    payload = f"{user_id}.{expiry}"
    signature = hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def session_user_id(value: str | None, now: int | None = None) -> UUID | None:
    if not value:
        return None
    try:
        user_id, expiry_text, signature = value.split(".")
        expiry = int(expiry_text)
        payload = f"{user_id}.{expiry}"
        expected = hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()
        current = int(time.time()) if now is None else now
        if expiry <= current or expiry > current + SESSION_SECONDS + 60:
            return None
        if not hmac.compare_digest(signature, expected):
            return None
        return UUID(user_id)
    except (ValueError, RuntimeError):
        return None


def get_session_user(request: Request, db: Db) -> User | None:
    user_id = session_user_id(request.cookies.get(SESSION_COOKIE))
    return db.get(User, user_id) if user_id else None


SessionUser = Annotated[User | None, Depends(get_session_user)]


def auth_guard(request: Request, user: SessionUser) -> None:
    path = request.url.path
    if (
        path in {"/health", "/docs", "/redoc", "/openapi.json"}
        or path == "/auth"
        or path.startswith("/auth/")
        or path.startswith("/verify/")
        or (path.startswith("/escrow/") and path.endswith("/seller-agree"))
    ):
        return
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "অনুগ্রহ করে প্রবেশ করুন")


def authenticated_user(user: SessionUser) -> User:
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "অনুগ্রহ করে প্রবেশ করুন")
    return user


def bootstrap_admin() -> None:
    username = settings.admin_username.strip()
    password = settings.admin_password.get_secret_value()
    if not username or not password:
        raise RuntimeError("ADMIN_USERNAME and ADMIN_PASSWORD must be configured")
    _secret()
    with SessionLocal.begin() as db:
        user = db.scalar(select(User).where(User.username == username))
        if user is None:
            user = db.scalar(select(User).order_by(User.created_at).limit(1))
        if user is None:
            db.add(User(username=username, password_hash=hash_password(password)))
        else:
            user.username = username
            if not verify_password(password, user.password_hash):
                user.password_hash = hash_password(password)
