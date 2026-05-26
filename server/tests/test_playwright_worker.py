import pytest

from app.workers.playwright_worker import run_playwright_review


@pytest.mark.slow
async def test_playwright_worker_basic():
    result = await run_playwright_review(
        url="https://example.com",
        viewports=["desktop", "mobile"],
        review_id="test-pw-01",
    )
    assert "desktop" in result.screenshots
    assert "mobile" in result.screenshots
    assert result.screenshots["desktop"].startswith("asset://")
    assert result.extracted_text.language_detected in ("en", "unknown")
    assert isinstance(result.wcag_extended.summary["violations_count"], int)
    assert isinstance(result.ctas_layout, dict)
