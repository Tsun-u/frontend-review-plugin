import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.auth import verify_bearer
from app.db import get_pool

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(prefix="/report", tags=["report"])


@router.get("/{review_id}", dependencies=[Depends(verify_bearer)], response_class=HTMLResponse)
async def get_report(review_id: str, request: Request):
    try:
        rid = uuid.UUID(review_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "BAD_URL", "message": "invalid review_id"},
        )

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT url, status, result_json, error_json FROM reviews WHERE id=$1", rid
        )
    if row is None:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "WORKER_FAILED", "message": "review not found"},
        )

    result_json = row["result_json"]
    error_json = row["error_json"]
    result = json.loads(result_json) if result_json else {}
    error = json.loads(error_json) if error_json else {}

    return templates.TemplateResponse(
        request,
        "report.html",
        {
            "review_id": review_id,
            "url": row["url"],
            "status": row["status"],
            "result": result,
            "error": error,
        },
    )
