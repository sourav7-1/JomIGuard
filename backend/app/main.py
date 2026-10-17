from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.documents import router as documents_router
from app.api.lands import router as lands_router
from app.api.meta import router as meta_router
from app.core.config import settings
from app.services.storage import get_storage


@asynccontextmanager
async def lifespan(app: FastAPI):
    # honour dependency overrides so tests never touch real MinIO
    app.dependency_overrides.get(get_storage, get_storage)().ensure_bucket()
    yield


app = FastAPI(title="JomiGuard API", lifespan=lifespan)
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


@app.get("/health")
def health():
    return {"status": "ok"}
