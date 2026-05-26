from datetime import timedelta
from io import BytesIO

from minio import Minio

from app.config import settings

_client = Minio(
    settings.minio_endpoint,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=settings.minio_secure,
)


def ensure_bucket() -> None:
    if not _client.bucket_exists(settings.minio_bucket):
        _client.make_bucket(settings.minio_bucket)


def put_asset(key: str, data: bytes, content_type: str) -> str:
    _client.put_object(
        settings.minio_bucket, key, BytesIO(data), len(data), content_type=content_type
    )
    return f"asset://{settings.minio_bucket}/{key}"


def signed_url(key: str, expires_minutes: int = 60) -> str:
    return _client.presigned_get_object(
        settings.minio_bucket, key, expires=timedelta(minutes=expires_minutes)
    )


def get_asset_object(key: str) -> tuple[bytes, str]:
    resp = _client.get_object(settings.minio_bucket, key)
    try:
        data = resp.read()
        content_type = resp.headers.get("Content-Type", "application/octet-stream")
        return data, content_type
    finally:
        resp.close()
        resp.release_conn()
