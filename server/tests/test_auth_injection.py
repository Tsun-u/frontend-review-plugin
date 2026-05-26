import asyncio
import json
import uuid

import asyncpg
import pytest
import httpx

API_BASE = "http://localhost:8000"
AUTH_HEADER = {"Authorization": "Bearer changeme-generate-with-openssl-rand-hex-32"}
DB_DSN = "postgresql://review:review@postgres:5432/review"

FAKE_COOKIE_VALUE = "FAKE_SESSION_TOKEN_12345"


@pytest.fixture
def api_client():
    return httpx.Client(base_url=API_BASE, timeout=180)


@pytest.mark.slow
def test_auth_cookie_injection(api_client):
    """Auth cookies should be injected into Playwright context."""
    r = api_client.post(
        "/review/objective",
        json={
            "url": "http://fixture-server/bad_contrast.html",
            "viewports": ["desktop"],
            "auth": {
                "cookies": [
                    {
                        "name": "JSESSIONID",
                        "value": FAKE_COOKIE_VALUE,
                        "domain": "fixture-server",
                        "path": "/",
                    }
                ]
            },
        },
        headers=AUTH_HEADER,
    )
    assert r.status_code == 200
    d = r.json()
    assert "review_id" in d
    assert len(d["screenshots"]) > 0
    assert any(
        "lighthouse" in w and "skipped" in w for w in d["worker_warnings"]
    ), "lighthouse should be skipped when auth is present"


@pytest.mark.slow
def test_auth_not_in_result(api_client):
    """SECURITY: auth credentials must never appear in response or DB."""
    r = api_client.post(
        "/review/objective",
        json={
            "url": "http://fixture-server/bad_contrast.html",
            "viewports": ["desktop"],
            "auth": {
                "cookies": [
                    {
                        "name": "SESSION",
                        "value": FAKE_COOKIE_VALUE,
                        "domain": "fixture-server",
                        "path": "/",
                    }
                ],
                "extra_headers": {"X-Secret": "HEADER_SECRET_67890"},
            },
        },
        headers=AUTH_HEADER,
    )
    assert r.status_code == 200
    response_text = r.text

    assert FAKE_COOKIE_VALUE not in response_text, (
        "Cookie value leaked into API response!"
    )
    assert "HEADER_SECRET_67890" not in response_text, (
        "Header secret leaked into API response!"
    )
    assert "auth" not in r.json() or r.json().get("auth") is None, (
        "auth field present in response!"
    )

    review_id = r.json()["review_id"]

    async def _check_db():
        conn = await asyncpg.connect(DB_DSN)
        row = await conn.fetchrow(
            "SELECT result_json::text AS r, error_json::text AS e FROM reviews WHERE id=$1",
            uuid.UUID(review_id),
        )
        await conn.close()
        return row

    row = asyncio.run(_check_db())
    if row["r"]:
        assert FAKE_COOKIE_VALUE not in row["r"], "Cookie value leaked into DB result_json!"
        assert "HEADER_SECRET_67890" not in row["r"], "Header secret leaked into DB result_json!"
    if row["e"]:
        assert FAKE_COOKIE_VALUE not in row["e"], "Cookie value leaked into DB error_json!"
        assert "HEADER_SECRET_67890" not in row["e"], "Header secret leaked into DB error_json!"


def test_auth_optional(api_client):
    """Request without auth should still work (backward compat)."""
    r = api_client.post(
        "/review/objective",
        json={"url": "http://fixture-server/bad_contrast.html", "viewports": ["desktop"]},
        headers=AUTH_HEADER,
    )
    assert r.status_code == 200
    d = r.json()
    assert "review_id" in d
