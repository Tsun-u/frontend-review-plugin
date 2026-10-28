import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from playwright.async_api import Error as PlaywrightError, async_playwright

from app.workers import playwright_worker
from app.workers.playwright_worker import _open_page

QUIET_PAGE = b"<html><body><h1>ready</h1></body></html>"
# Polls every 200 ms, so the network never stays quiet for the 500 ms that
# networkidle needs, the way a Cloudflare Turnstile widget behaves.
POLLING_PAGE = (
    b"<html><body><h1>ready</h1>"
    b"<script>setInterval(() => fetch('/ping?' + Date.now()), 200)</script>"
    b"</body></html>"
)


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = {"/quiet": QUIET_PAGE, "/polling": POLLING_PAGE}.get(self.path.split("?")[0], b"pong")
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture
def base_url():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


async def _open_and_read_heading(url: str) -> tuple[str, float]:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        started = time.monotonic()
        await _open_page(page, url)
        elapsed = time.monotonic() - started
        heading = await page.inner_text("h1")
        await browser.close()
        return heading, elapsed


@pytest.mark.slow
async def test_page_that_never_goes_idle_opens_after_the_capped_wait(base_url, monkeypatch):
    monkeypatch.setattr(playwright_worker, "NETWORK_IDLE_TIMEOUT_MS", 1000)
    heading, elapsed = await _open_and_read_heading(f"{base_url}/polling")
    assert heading == "ready"
    assert 1.0 <= elapsed < 5.0


@pytest.mark.slow
async def test_quiet_page_opens_without_waiting_out_the_cap(base_url):
    heading, elapsed = await _open_and_read_heading(f"{base_url}/quiet")
    assert heading == "ready"
    assert elapsed < playwright_worker.NETWORK_IDLE_TIMEOUT_MS / 1000


@pytest.mark.slow
async def test_unreachable_url_still_fails():
    with pytest.raises(PlaywrightError):
        await _open_and_read_heading("http://127.0.0.1:9/")
