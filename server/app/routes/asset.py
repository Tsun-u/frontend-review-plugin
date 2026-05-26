from fastapi import APIRouter, Depends, HTTPException, Response
from minio.error import S3Error

from app.auth import verify_bearer
from app.storage import get_asset_object

router = APIRouter(prefix="/asset", tags=["asset"])


@router.get("/{review_id}/{filename}", dependencies=[Depends(verify_bearer)])
async def get_asset(review_id: str, filename: str):
    key = f"{review_id}/{filename}"
    try:
        data, content_type = get_asset_object(key)
    except S3Error:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "WORKER_FAILED",
                "message": f"asset not found: {key}",
            },
        )
    return Response(content=data, media_type=content_type)
