from pathlib import Path

import pytest
from playwright.async_api import async_playwright

CHECKER_JS = Path(__file__).parent.parent / "app" / "workers" / "wcag" / "apca-wcag-checker.js"
FIXTURES = Path(__file__).parent / "fixtures" / "wcag_test_pages"


async def run_checker(html_file: str, viewport: str = "desktop") -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(
            viewport={"width": 375, "height": 667} if viewport == "mobile"
            else {"width": 1280, "height": 720}
        )
        page = await ctx.new_page()
        await page.goto(f"file:///{(FIXTURES / html_file).as_posix()}")
        await page.add_script_tag(content=CHECKER_JS.read_text())
        result = await page.evaluate(f"window.__apcaWcagCheck({{viewport: '{viewport}'}})")
        await browser.close()
        return result


@pytest.mark.slow
async def test_contrast_fail_detected():
    r = await run_checker("contrast_fail.html")
    assert any(v["rule"] == "contrast" for v in r["violations"])
    contrast_v = next(v for v in r["violations"] if v["rule"] == "contrast")
    assert contrast_v["wcag2"]["ratio"] < 4.5
    assert contrast_v["apca"]["lc"] < 60


@pytest.mark.slow
async def test_contrast_pass_no_violation():
    r = await run_checker("contrast_pass.html")
    contrast_violations = [v for v in r["violations"] if v["rule"] == "contrast"]
    assert len(contrast_violations) == 0


@pytest.mark.slow
async def test_tap_target_mobile_fail():
    r = await run_checker("tap_target_fail.html", viewport="mobile")
    assert any(v["rule"] == "tap_target" for v in r["violations"])


@pytest.mark.slow
async def test_tap_target_desktop_skipped():
    r = await run_checker("tap_target_fail.html", viewport="desktop")
    tap_violations = [v for v in r["violations"] if v["rule"] == "tap_target"]
    assert len(tap_violations) == 0


@pytest.mark.slow
async def test_focus_indicator_missing():
    r = await run_checker("focus_outline_none.html")
    assert any(v["rule"] == "focus_indicator_missing" for v in r["violations"])


@pytest.mark.slow
async def test_text_overflow_no_title():
    r = await run_checker("overflow_no_title.html")
    assert any(v["rule"] == "text_overflow_no_title" for v in r["violations"])


@pytest.mark.slow
async def test_summary_structure():
    r = await run_checker("contrast_fail.html")
    assert "summary" in r
    assert "violations_count" in r["summary"]
    assert "by_severity" in r["summary"]
    assert sum(r["summary"]["by_severity"].values()) == r["summary"]["violations_count"]
