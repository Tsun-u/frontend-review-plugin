from pathlib import Path

import pytest
from playwright.async_api import async_playwright

TEXT_STYLING_JS = Path(__file__).parent.parent / "app" / "workers" / "text_styling.js"
FIXTURE = Path(__file__).parent / "fixtures" / "integration_pages" / "text_styling_test.html"


async def run_extractor(html_file: Path) -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(f"file:///{html_file.as_posix()}")
        await page.add_script_tag(content=TEXT_STYLING_JS.read_text())
        result = await page.evaluate("window.__extractTextStyling()")
        await browser.close()
        return result


@pytest.mark.slow
async def test_extracts_link_without_underline():
    r = await run_extractor(FIXTURE)
    links = [e for e in r["elements"] if e["is_link"]]
    assert len(links) >= 2
    no_underline = [e for e in links if "underline" not in e["text_decoration_line"]]
    assert len(no_underline) >= 1
    assert r["summary"]["links_without_underline"] >= 1


@pytest.mark.slow
async def test_extracts_line_through():
    r = await run_extractor(FIXTURE)
    strikethrough = [e for e in r["elements"] if "line-through" in e["text_decoration_line"]]
    assert len(strikethrough) >= 1
    assert r["summary"]["line_through_count"] >= 1


@pytest.mark.slow
async def test_extracts_bold():
    r = await run_extractor(FIXTURE)
    bold = [e for e in r["elements"] if int(e["font_weight"]) >= 600]
    assert len(bold) >= 1
    assert r["summary"]["bold_count"] >= 1


@pytest.mark.slow
async def test_extracts_italic():
    r = await run_extractor(FIXTURE)
    italic = [e for e in r["elements"] if e["font_style"] == "italic"]
    assert len(italic) >= 1
    assert italic[0]["text"].startswith("引用")


@pytest.mark.slow
async def test_skips_normal_text():
    r = await run_extractor(FIXTURE)
    normal = [e for e in r["elements"] if e["text"].startswith("普通內文")]
    assert len(normal) == 0
