from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from app.auth import verify_bearer
from app.db import close_pool, get_pool
from app.routes import asset, report, review
from app.storage import ensure_bucket


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await get_pool()
    ensure_bucket()
    yield
    await close_pool()


app = FastAPI(
    title="frontend-review-server",
    version="0.1.0",
    lifespan=lifespan,
    root_path="/frontend-review",
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/health/protected", dependencies=[Depends(verify_bearer)])
async def health_protected():
    return {"status": "ok", "auth": "verified"}


app.include_router(asset.router)
app.include_router(review.router)
app.include_router(report.router)
