from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.documents import router as documents_router
from app.services.storage import get_storage


@asynccontextmanager
async def lifespan(app: FastAPI):
    # honour dependency overrides so tests never touch real MinIO
    app.dependency_overrides.get(get_storage, get_storage)().ensure_bucket()
    yield


app = FastAPI(title="JomiGuard API", lifespan=lifespan)
app.include_router(documents_router)

@app.get("/health")
def health():
    return {"status": "ok"}
