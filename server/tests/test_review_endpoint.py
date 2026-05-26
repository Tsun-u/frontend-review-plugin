import pytest


@pytest.mark.slow
async def test_review_objective_end_to_end(client):
    r = await client.post(
        "/review/objective",
        json={"url": "https://example.com", "viewports": ["desktop"]},
        headers={"Authorization": "Bearer test-key-do-not-use-in-prod"},
        timeout=180,
    )
    assert r.status_code == 200
    data = r.json()
    assert "review_id" in data
    assert "lighthouse" in data
    assert "wcag_extended" in data
    assert "screenshots" in data
    assert "worker_warnings" in data
    assert isinstance(data["worker_warnings"], list)


async def test_review_bad_url(client):
    r = await client.post(
        "/review/objective",
        json={"url": "not-a-url"},
        headers={"Authorization": "Bearer test-key-do-not-use-in-prod"},
    )
    assert r.status_code == 422


async def test_review_requires_auth(client):
    r = await client.post(
        "/review/objective",
        json={"url": "https://example.com"},
    )
    assert r.status_code == 401
