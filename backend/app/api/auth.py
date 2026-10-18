import threading
import time
from collections import defaultdict, deque
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import (
    SESSION_COOKIE,
    SESSION_SECONDS,
    authenticated_user,
    hash_password,
    issue_session,
    verify_password,
)
from app.core.config import settings
from app.db.session import get_db
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(authenticated_user)]
_attempts: dict[str, deque[float]] = defaultdict(deque)
_attempts_lock = threading.Lock()
_dummy_hash = hash_password("invalid login")


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=1024)


class UserOut(BaseModel):
    id: str
    username: str


def clear_login_attempts() -> None:
    with _attempts_lock:
        _attempts.clear()


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, request: Request, response: Response, db: Db):
    address = request.client.host if request.client else "unknown"
    now = time.monotonic()
    with _attempts_lock:
        attempts = _attempts[address]
        while attempts and now - attempts[0] >= 60:
            attempts.popleft()
        if len(attempts) >= 5:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "এক মিনিট পরে আবার চেষ্টা করুন")
        attempts.append(now)

    user = db.scalar(select(User).where(User.username == body.username))
    valid = verify_password(body.password, user.password_hash if user else _dummy_hash)
    if not user or not valid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "ব্যবহারকারীর নাম বা পাসওয়ার্ড সঠিক নয়")

    with _attempts_lock:
        _attempts[address].clear()
    response.set_cookie(
        SESSION_COOKIE,
        issue_session(user.id),
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return UserOut(id=str(user.id), username=user.username)


@router.post("/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie(
        SESSION_COOKIE,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return UserOut(id=str(user.id), username=user.username)
