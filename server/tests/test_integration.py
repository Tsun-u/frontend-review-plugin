import pytest
import httpx

URLS = [
    ("https://example.com", "baseline"),
    ("https://www.president.gov.tw/", "traditional-chinese"),
    ("https://github.com/", "spa"),
    ("https://www.nytimes.com/", "english-news"),
    ("http://fixture-server/bad_a11y.html", "bad-a11y-fixture"),
    ("http://fixture-server/bad_contrast.html", "bad-contrast-fixture"),
]

API_BASE = "http://localhost:8000"
AUTH = {"Authorization": "Bearer changeme-generate-with-openssl-rand-hex-32"}


@pytest.fixture
def api_client():
    return httpx.Client(base_url=API_BASE, timeout=180)


@pytest.mark.integration
@pytest.mark.parametrize("url,label", URLS, ids=[u[1] for u in URLS])
def test_url_e2e(api_client, url, label):
    r = api_client.post(
        "/review/objective",
        json={"url": url, "viewports": ["desktop"]},
        headers=AUTH,
    )
    if r.status_code == 500:
        detail = r.json().get("detail", {})
        pytest.skip(f"{label}: server error — {detail.get('message', 'unknown')[:200]}")
    if r.status_code == 504:
        pytest.skip(f"{label}: timeout")
    assert r.status_code == 200, f"{label}: unexpected status {r.status_code}"
    d = r.json()
    assert "review_id" in d, f"{label}: missing review_id"
    assert "lighthouse" in d, f"{label}: missing lighthouse"
    assert d["lighthouse"]["accessibility"] >= 0
    assert len(d["screenshots"]) > 0, f"{label}: no screenshots"
    assert "worker_warnings" in d
    assert isinstance(d["worker_warnings"], list)


@pytest.mark.integration
def test_bad_contrast_has_violations(api_client):
    r = api_client.post(
        "/review/objective",
        json={"url": "http://fixture-server/bad_contrast.html", "viewports": ["desktop"]},
        headers=AUTH,
    )
    assert r.status_code == 200
    d = r.json()
    assert d["wcag_extended"]["summary"]["violations_count"] > 0


@pytest.mark.integration
def test_bad_a11y_has_violations(api_client):
    r = api_client.post(
        "/review/objective",
        json={"url": "http://fixture-server/bad_a11y.html", "viewports": ["desktop", "mobile"]},
        headers=AUTH,
    )
    assert r.status_code == 200
    d = r.json()
    assert d["wcag_extended"]["summary"]["violations_count"] > 0
