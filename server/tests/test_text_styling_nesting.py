from pathlib import Path

import pytest
from playwright.async_api import async_playwright

TEXT_STYLING_JS = Path(__file__).parent.parent / "app" / "workers" / "text_styling.js"
FIXTURE = Path(__file__).parent / "fixtures" / "nesting.html"


@pytest.mark.slow
async def test_leaf_only_no_double_count():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(f"file:///{FIXTURE.as_posix()}")
        await page.add_script_tag(content=TEXT_STYLING_JS.read_text())
        r = await page.evaluate("window.__extractTextStyling()")
        await browser.close()

    assert r["summary"]["bold_count"] == 2, f"expected 2 bold (strong + p), got {r['summary']['bold_count']}"
    assert r["summary"]["links_total"] == 1, f"expected 1 link, got {r['summary']['links_total']}"
