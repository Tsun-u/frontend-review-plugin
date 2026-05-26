import asyncio
import json
import uuid

from app.config import settings
from app.db import get_pool
from app.models import ReviewRequest
from app.storage import _client as minio_client
from app.workers.deepgaze_worker import run_deepgaze
from app.workers.playwright_worker import run_playwright_review
from app.workers.readability_worker import run_readability


async def run_review(req: ReviewRequest) -> dict:
    review_id = str(uuid.uuid4())
    pool = await get_pool()

    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO reviews (id, url, status) VALUES ($1, $2, 'running')",
            uuid.UUID(review_id),
            str(req.url),
        )

    worker_warnings: list[str] = []

    try:
        pw_result = await asyncio.wait_for(
            run_playwright_review(str(req.url), req.viewports, review_id, auth=req.auth),
            timeout=90,
        )
        worker_warnings.extend(pw_result.warnings)

        dg_result = None
        if not req.options.skip_deepgaze:
            try:
                desktop_key = f"{review_id}/desktop.png"
                stat = minio_client.get_object(settings.minio_bucket, desktop_key)
                screenshot_bytes = stat.read()
                stat.close()
                stat.release_conn()

                ctas_desktop = pw_result.ctas_layout.get("desktop", [])
                dg_result = await asyncio.wait_for(
                    run_deepgaze(
                        screenshot_bytes,
                        review_id,
                        "desktop",
                        ctas_layout=ctas_desktop,
                    ),
                    timeout=30,
                )
            except asyncio.TimeoutError:
                worker_warnings.append("deepgaze: timed out after 30s")
            except Exception as e:
                worker_warnings.append(f"deepgaze: {type(e).__name__}: {str(e)[:200]}")

        all_text = " ".join(pw_result.extracted_text.by_section.values())
        rd_result = run_readability(
            all_text,
            pw_result.extracted_text.language_detected,
            chinese_target_level=req.options.chinese_target_level,
        )

        result = {
            "review_id": review_id,
            "lighthouse": pw_result.lighthouse.model_dump(),
            "axe_violations": [v.model_dump() for v in pw_result.axe_violations],
            "wcag_extended": pw_result.wcag_extended.model_dump(),
            "screenshots": pw_result.screenshots,
            "dom_html": pw_result.dom_html,
            "extracted_text": pw_result.extracted_text.model_dump(),
            "deepgaze": dg_result.model_dump() if dg_result else None,
            "english_readability": rd_result.english.model_dump() if rd_result.english else None,
            "chinese_readability": rd_result.chinese.model_dump() if rd_result.chinese else None,
            "text_styling": pw_result.text_styling.model_dump() if pw_result.text_styling else None,
            "worker_warnings": worker_warnings,
        }

        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE reviews SET status='completed', result_json=$1, completed_at=NOW() WHERE id=$2",
                json.dumps(result),
                uuid.UUID(review_id),
            )
        return result

    except asyncio.TimeoutError:
        error = {"error_code": "TIMEOUT", "message": "playwright worker timed out after 90s"}
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE reviews SET status='failed', error_json=$1 WHERE id=$2",
                json.dumps(error),
                uuid.UUID(review_id),
            )
        raise

    except Exception as e:
        error = {"error_code": "INTERNAL", "message": str(e)[:500]}
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE reviews SET status='failed', error_json=$1 WHERE id=$2",
                json.dumps(error),
                uuid.UUID(review_id),
            )
        raise
