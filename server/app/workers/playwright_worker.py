import asyncio
import json
import os
import tempfile
from pathlib import Path

from langdetect import detect
from playwright.async_api import async_playwright

from app.models import (
    AxeViolation,
    ExtractedText,
    LighthouseScore,
    PlaywrightWorkerOutput,
    ReviewAuth,
    TextStyling,
    WcagExtended,
)
from app.storage import put_asset

CHECKER_JS = (Path(__file__).parent / "wcag" / "apca-wcag-checker.js").read_text()
TEXT_STYLING_JS = (Path(__file__).parent / "text_styling.js").read_text()

AXE_CORE_PATH = Path(__file__).parent / "wcag" / "axe.min.js"

VIEWPORT_SIZES = {
    # width/height = CSS viewport (DIP); dsf = device_scale_factor (DPR)
    # desktop: 公司採購螢幕標準 1920x1080 @ DPR 1
    # mobile:  公務手機 720x1440 physical, hdpi → CSS 480x960 @ DPR 1.5
    "desktop": {"width": 1920, "height": 1080, "dsf": 1.0},
    "tablet": {"width": 768, "height": 1024, "dsf": 2.0},
    "mobile": {"width": 480, "height": 960, "dsf": 1.5},
}


async def _inject_auth(ctx, auth: ReviewAuth | None) -> None:
    if not auth:
        return
    try:
        if auth.cookies:
            await ctx.add_cookies([c.model_dump() for c in auth.cookies])
        if auth.extra_headers:
            await ctx.set_extra_http_headers(auth.extra_headers)
    except Exception:
        raise ValueError("auth injection failed: invalid cookie or header format")


async def run_playwright_review(
    url: str, viewports: list[str], review_id: str, auth: ReviewAuth | None = None
) -> PlaywrightWorkerOutput:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        screenshots: dict[str, str] = {}
        wcag_results: dict[str, dict] = {}
        ctas_layout: dict[str, list[dict]] = {}
        text_styling_result: dict | None = None
        dom_html = ""
        extracted_text_by_section: dict[str, str] = {}

        for viewport in viewports:
            vp = VIEWPORT_SIZES[viewport]
            ctx = await browser.new_context(
                viewport={"width": vp["width"], "height": vp["height"]},
                device_scale_factor=vp["dsf"],
            )
            await _inject_auth(ctx, auth)
            page = await ctx.new_page()
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(500)

            png = await page.screenshot(full_page=True)
            key = f"{review_id}/{viewport}.png"
            put_asset(key, png, "image/png")
            screenshots[viewport] = f"asset://{key}"

            await page.add_script_tag(content=CHECKER_JS)
            wcag = await page.evaluate(
                f"window.__apcaWcagCheck({{viewport: '{viewport}'}})"
            )
            wcag_results[viewport] = wcag

            cta_list = await _extract_cta_layout(page)
            ctas_layout[viewport] = cta_list

            if viewport == "desktop":
                dom_html = await page.content()
                extracted_text_by_section = await _extract_text_by_section(page)
                await page.add_script_tag(content=TEXT_STYLING_JS)
                text_styling_result = await page.evaluate("window.__extractTextStyling()")

            await ctx.close()

        await browser.close()

    dom_key = f"{review_id}/dom.html"
    put_asset(dom_key, dom_html.encode("utf-8"), "text/html")

    all_text = " ".join(extracted_text_by_section.values()).strip()
    lang = _detect_language(all_text)

    wcag_merged = _merge_wcag_results(wcag_results)
    lighthouse_score, lh_warning = await _run_lighthouse(url, auth)
    axe_violations, axe_warning = await _run_axe(url, auth)

    warnings = [w for w in [lh_warning, axe_warning] if w is not None]

    return PlaywrightWorkerOutput(
        lighthouse=lighthouse_score,
        axe_violations=axe_violations,
        wcag_extended=WcagExtended(**wcag_merged),
        screenshots=screenshots,
        dom_html=f"asset://{dom_key}",
        extracted_text=ExtractedText(
            by_section=extracted_text_by_section, language_detected=lang
        ),
        ctas_layout=ctas_layout,
        text_styling=TextStyling(**text_styling_result) if text_styling_result else None,
        warnings=warnings,
    )


async def _extract_text_by_section(page) -> dict[str, str]:
    return await page.evaluate(
        """(() => {
        const out = {};
        const sections = {
            header: document.querySelector('header'),
            main: document.querySelector('main') || document.body,
            footer: document.querySelector('footer'),
        };
        for (const [name, el] of Object.entries(sections)) {
            if (el) out[name] = el.innerText.trim();
        }
        return out;
    })()"""
    )


async def _extract_cta_layout(page) -> list[dict]:
    return await page.evaluate(
        """(() => {
        const sel = "button, a[role='button'], input[type='submit'], input[type='button']";
        const els = document.querySelectorAll(sel);
        const getSelector = (el) => el.id ? '#' + el.id :
            el.tagName.toLowerCase() + '.' + ((el.className||'').trim().split(/\\s+/).slice(0,2).join('.'));
        const out = [];
        for (const el of els) {
            const r = el.getBoundingClientRect();
            out.push({
                selector: getSelector(el),
                bbox: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
            });
        }
        return out;
    })()"""
    )


def _detect_language(text: str) -> str:
    if not text.strip():
        return "unknown"
    cjk = sum(1 for c in text if "一" <= c <= "鿿")
    if cjk / max(len(text), 1) >= 0.15:
        return "zh-tw"
    try:
        return detect(text[:1000])
    except Exception:
        return "unknown"


def _merge_wcag_results(results: dict[str, dict]) -> dict:
    all_violations = []
    for viewport, r in results.items():
        for v in r["violations"]:
            v["viewport"] = viewport
            all_violations.append(v)
    by_sev = {"critical": 0, "major": 0, "minor": 0}
    for v in all_violations:
        by_sev[v["severity"]] = by_sev.get(v["severity"], 0) + 1
    return {
        "summary": {"violations_count": len(all_violations), "by_severity": by_sev},
        "violations": all_violations,
    }


async def _run_lighthouse(url: str, auth: ReviewAuth | None = None) -> tuple[LighthouseScore, str | None]:
    zero = LighthouseScore(performance=0, accessibility=0, best_practices=0, seo=0)
    headers_file = None
    extra_args: list[str] = []
    try:
        if auth and (auth.cookies or auth.extra_headers):
            headers: dict[str, str] = {}
            if auth.extra_headers:
                headers.update(auth.extra_headers)
            if auth.cookies:
                cookie_str = "; ".join(f"{c.name}={c.value}" for c in auth.cookies)
                existing = headers.get("Cookie")
                headers["Cookie"] = f"{existing}; {cookie_str}" if existing else cookie_str
            fd, headers_file = tempfile.mkstemp(suffix=".json")
            os.write(fd, json.dumps(headers).encode("utf-8"))
            os.close(fd)
            os.chmod(headers_file, 0o600)
            extra_args = [f"--extra-headers={headers_file}"]
        proc = await asyncio.create_subprocess_exec(
            "lighthouse",
            url,
            "--output=json",
            "--quiet",
            "--chrome-path=/usr/bin/google-chrome",
            "--chrome-flags=--headless=new --no-sandbox --disable-dev-shm-usage",
            "--only-categories=performance,accessibility,best-practices,seo",
            *extra_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        if proc.returncode != 0:
            return zero, f"lighthouse: exited with code {proc.returncode}"
        data = json.loads(stdout)
        cats = data["categories"]
        return LighthouseScore(
            performance=int((cats["performance"]["score"] or 0) * 100),
            accessibility=int((cats["accessibility"]["score"] or 0) * 100),
            best_practices=int((cats["best-practices"]["score"] or 0) * 100),
            seo=int((cats["seo"]["score"] or 0) * 100),
        ), None
    except asyncio.TimeoutError:
        return zero, "lighthouse: timed out after 60s"
    except FileNotFoundError:
        return zero, "lighthouse: CLI not found"
    except (json.JSONDecodeError, KeyError) as e:
        return zero, f"lighthouse: failed to parse output ({e})"
    finally:
        if headers_file and os.path.exists(headers_file):
            os.remove(headers_file)


async def _run_axe(url: str, auth: ReviewAuth | None = None) -> tuple[list[AxeViolation], str | None]:
    if not AXE_CORE_PATH.exists():
        return [], "axe: axe.min.js not found"
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            ctx = await browser.new_context()
            await _inject_auth(ctx, auth)
            page = await ctx.new_page()
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.add_script_tag(content=AXE_CORE_PATH.read_text())
            results = await page.evaluate(
                """async () => {
                const r = await axe.run({ runOnly: ['wcag2a', 'wcag2aa', 'wcag21aa'] });
                return r.violations;
            }"""
            )
            await browser.close()

        out = []
        for v in results:
            for node in v.get("nodes", []):
                target = node.get("target", ["unknown"])
                out.append(
                    AxeViolation(
                        rule=v["id"],
                        node=target[0] if target else "unknown",
                        impact=v.get("impact", "minor"),
                    )
                )
        return out, None
    except Exception as e:
        return [], f"axe: {type(e).__name__}: {str(e)[:200]}"
