import os

os.environ["REVIEW_API_MASTER_KEY"] = "test-key-do-not-use-in-prod"
os.environ.setdefault("POSTGRES_DSN", "postgresql://review:review@postgres:5432/review")
os.environ.setdefault("MINIO_ENDPOINT", "minio:9000")
os.environ.setdefault("MINIO_ACCESS_KEY", "minio")
os.environ.setdefault("MINIO_SECRET_KEY", "minio12345")

import app.config  # noqa: E402

app.config.settings = app.config.Settings()

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.main import app as fastapi_app  # noqa: E402


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as ac:
        yield ac
