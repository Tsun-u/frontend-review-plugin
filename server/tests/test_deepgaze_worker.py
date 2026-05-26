from pathlib import Path

import pytest

from app.workers.deepgaze_worker import run_deepgaze

FIXTURE = Path(__file__).parent / "fixtures" / "sample_screenshot.png"


@pytest.mark.slow
async def test_deepgaze_produces_heatmap():
    screenshot_bytes = FIXTURE.read_bytes()
    result = await run_deepgaze(
        screenshot_bytes=screenshot_bytes,
        review_id="test-dg-01",
        viewport="desktop",
    )
    assert result.saliency_heatmap.startswith("asset://")
    assert result.saliency_overlay.startswith("asset://")
    assert len(result.top_fixation_points) == 10
    for p in result.top_fixation_points:
        assert p.weight > 0
    assert result.ctas_detected == []
