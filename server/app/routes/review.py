import asyncio

from fastapi import APIRouter, Depends, HTTPException

from app.auth import verify_bearer
from app.models import ReviewRequest, SourceScanProject, SourceScanRequest
from app.source_scan_core import analyze_extracted_strings
from app.orchestrator import run_review

router = APIRouter(prefix="/review", tags=["review"])


@router.post("/objective", dependencies=[Depends(verify_bearer)])
async def post_review_objective(req: ReviewRequest):
    try:
        result = await run_review(req)
        return result
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail={"error_code": "TIMEOUT", "message": "review timed out"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error_code": "INTERNAL", "message": str(e)[:500]},
        )


MAX_SCAN_STRINGS = 5000


@router.post("/source-scan", dependencies=[Depends(verify_bearer)])
async def post_source_scan(req: SourceScanRequest):
    if len(req.strings) > MAX_SCAN_STRINGS:
        raise HTTPException(
            status_code=413,
            detail={
                "error_code": "BAD_URL",
                "message": f"too many strings: {len(req.strings)} > {MAX_SCAN_STRINGS}",
            },
        )
    if not req.strings:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "BAD_URL", "message": "strings is empty"},
        )
    try:
        whitelist = set(req.jargon_whitelist) if req.jargon_whitelist else None
        core_result = analyze_extracted_strings(
            [s.model_dump() for s in req.strings],
            expected_level=req.expected_level,
            jargon_whitelist=whitelist,
        )
        return SourceScanProject(**core_result)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error_code": "INTERNAL", "message": str(e)[:500]},
        )
