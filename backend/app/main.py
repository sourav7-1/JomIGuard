from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.api.escrow import router as escrow_router
from app.api.guardian import router as guardian_router
from app.api.identity import router as identity_router
from app.api.lands import router as lands_router
from app.api.meta import router as meta_router
from app.core.auth import auth_guard, bootstrap_admin
from app.core.config import settings
from app.db.session import get_db
from app.services.storage import get_storage


@asynccontextmanager
async def lifespan(app: FastAPI):
    # honour dependency overrides so tests never touch real MinIO
    app.dependency_overrides.get(get_storage, get_storage)().ensure_bucket()
    if get_db not in app.dependency_overrides:
        bootstrap_admin()
    yield


app = FastAPI(title="JomiGuard API", lifespan=lifespan, dependencies=[Depends(auth_guard)])
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(documents_router)
app.include_router(lands_router)
app.include_router(meta_router)
app.include_router(auth_router)
app.include_router(identity_router)
app.include_router(guardian_router)
app.include_router(escrow_router)


@app.get("/health")
def health():
    return {"status": "ok"}
